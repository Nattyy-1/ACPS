import datetime

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin, IsApplicant, IsInspector, IsSeniorOfficer
from applications.models import Application, ApplicationHistory
from notifications.models import Notification
from .models import Inspection, InspectionChecklistTemplate, InspectionChecklistItem, InspectionPhoto
from .serializers import (
    InspectionSerializer, InspectionChecklistItemSerializer,
    InspectionChecklistUpdateSerializer, InspectionPhotoSerializer,
)


def round_robin_inspector():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    inspectors = User.objects.filter(role="INSPECTOR", is_active=True)
    if not inspectors:
        return None
    active_statuses = {Inspection.Status.SCHEDULED, Inspection.Status.IN_PROGRESS}
    counts = (
        Inspection.objects.filter(
            assigned_inspector__in=inspectors,
            status__in=active_statuses,
        )
        .values("assigned_inspector")
        .annotate(count=Count("id"))
    )
    count_map = {str(c["assigned_inspector"]): c["count"] for c in counts}
    best = min(inspectors, key=lambda o: count_map.get(str(o.id), 0))
    return best


def auto_schedule_inspections(app):
    from datetime import timedelta
    from django.utils import timezone

    now = timezone.now()
    category = app.building_category
    schedules = []

    base_milestones = [
        (Inspection.InspectionType.FOUNDATION, timedelta(days=14)),
    ]

    if category in ("B", "C"):
        base_milestones.append(
            (Inspection.InspectionType.STRUCTURAL_FRAME, timedelta(days=60))
        )

    for insp_type, offset in base_milestones:
        inspector = round_robin_inspector()
        scheduled = now + offset
        inspection = Inspection.objects.create(
            application=app,
            inspection_type=insp_type,
            scheduled_date=scheduled,
            assigned_inspector=inspector,
            status=Inspection.Status.SCHEDULED,
        )
        schedules.append((inspection, inspector))

    return schedules


class CommenceConstructionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def post(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id, applicant=request.user)

        if app.status != Application.Status.PERMIT_ISSUED:
            return Response(
                {"detail": f"Cannot commence when status is {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start_date = request.data.get("start_date")
        contractor_name = request.data.get("contractor_name", "").strip()
        contractor_license = request.data.get("contractor_license", "").strip()
        supervisor_name = request.data.get("supervisor_name", "").strip()
        supervisor_phone = request.data.get("supervisor_phone", "").strip()

        if not all([start_date, contractor_name, contractor_license, supervisor_name, supervisor_phone]):
            return Response(
                {"detail": "All fields are required: start_date, contractor_name, contractor_license, supervisor_name, supervisor_phone."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            app.contractor_name = contractor_name
            app.contractor_license = contractor_license
            app.save(update_fields=["contractor_name", "contractor_license"])

            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.UNDER_CONSTRUCTION,
                actor=request.user,
                note=f"Construction commenced. Contractor: {contractor_name}, Supervisor: {supervisor_name}.",
            )
            app.status = Application.Status.UNDER_CONSTRUCTION
            app.save(update_fields=["status"])

            schedules = auto_schedule_inspections(app)

        inspections_data = []
        for inspection, inspector in schedules:
            inspections_data.append({
                "inspection_id": str(inspection.id),
                "inspection_type": inspection.inspection_type,
                "scheduled_date": inspection.scheduled_date.isoformat(),
                "assigned_inspector_name": inspector.full_name if inspector else None,
            })

            if inspector:
                send_mail(
                    subject="Inspection Scheduled",
                    message=(
                        f"Dear {inspector.full_name},\n\n"
                        f"You have been assigned a {inspection.get_inspection_type_display()}.\n"
                        f"Application: {app.arn}\n"
                        f"Site Address: {app.plot_address}, Subcity: {app.subcity_id}\n"
                        f"Scheduled Date: {inspection.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                        f"GPS: {app.plot_gps_lat}, {app.plot_gps_lng}\n"
                        f"Supervisor: {supervisor_name} ({supervisor_phone})\n\n"
                        f"Thank you."
                    ),
                    from_email=None,
                    recipient_list=[inspector.email],
                )
                Notification.objects.create(
                    recipient=inspector,
                    title="Inspection Assigned",
                    body=f"{inspection.get_inspection_type_display()} scheduled for {app.arn} on {inspection.scheduled_date.strftime('%Y-%m-%d')}.",
                    notification_type="INSPECTION_ASSIGNED",
                    reference_id=str(inspection.id),
                    reference_type="INSPECTION",
                )

            applicant = app.applicant
            send_mail(
                subject="Construction Commenced & Inspection Scheduled",
                message=(
                    f"Dear {applicant.full_name},\n\n"
                    f"Construction has been commenced for {app.arn}.\n"
                    f"Contractor: {contractor_name}\n"
                    f"Supervisor: {supervisor_name} ({supervisor_phone})\n\n"
                    f"A {inspection.get_inspection_type_display()} has been scheduled for "
                    f"{inspection.scheduled_date.strftime('%Y-%m-%d %H:%M')}.\n"
                    f"Inspector: {inspector.full_name if inspector else 'To be assigned'}\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[applicant.email],
            )

        Notification.objects.create(
            recipient=request.user,
            title="Construction Commenced",
            body=f"Construction commenced for {app.arn}. {len(schedules)} inspection(s) scheduled.",
            notification_type="CONSTRUCTION_COMMENCED",
            reference_id=str(app.id),
            reference_type="APPLICATION",
        )

        return Response({
            "application_id": str(app.id),
            "arn": app.arn,
            "status": app.status,
            "contractor_name": contractor_name,
            "contractor_license": contractor_license,
            "supervisor_name": supervisor_name,
            "supervisor_phone": supervisor_phone,
            "start_date": start_date,
            "inspections": inspections_data,
        })


class ApplicationInspectionListView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id)

        user = request.user
        if user.role == "APPLICANT" and app.applicant != user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if user.role == "INSPECTOR" and not Inspection.objects.filter(application=app, assigned_inspector=user).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        inspections = app.inspections.all().order_by("scheduled_date")
        serializer = InspectionSerializer(inspections, many=True)
        return Response(serializer.data)


class InspectorScheduleView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsInspector]

    def get(self, request):
        qs = Inspection.objects.filter(
            assigned_inspector=request.user,
            status__in=[Inspection.Status.SCHEDULED, Inspection.Status.IN_PROGRESS],
        ).order_by("scheduled_date").select_related("application")

        results = []
        for insp in qs:
            app = insp.application
            results.append({
                "inspection_id": str(insp.id),
                "inspection_type": insp.inspection_type,
                "inspection_type_label": insp.get_inspection_type_display(),
                "scheduled_date": insp.scheduled_date.isoformat(),
                "status": insp.status,
                "application": {
                    "id": str(app.id),
                    "arn": app.arn,
                    "plot_address": app.plot_address,
                    "subcity_id": app.subcity_id,
                    "woreda": app.woreda,
                    "plot_gps_lat": float(app.plot_gps_lat),
                    "plot_gps_lng": float(app.plot_gps_lng),
                    "building_category": app.building_category,
                    "contractor_name": app.contractor_name,
                    "supervisor_name": "",
                    "supervisor_phone": "",
                },
            })

        return Response(results)


class InspectionDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsInspector()]
        return [IsInspector()]

    def get(self, request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id)

        if request.user.role == "INSPECTOR" and inspection.assigned_inspector != request.user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        qs = InspectionChecklistTemplate.objects.filter(
            inspection_type=inspection.inspection_type, is_active=True
        ).order_by("order")

        existing_items = {str(i.item_template_id): i for i in inspection.checklist_items.all() if i.item_template_id}
        for template in qs:
            if str(template.id) not in existing_items:
                InspectionChecklistItem.objects.create(
                    inspection=inspection,
                    item_template=template,
                    item_text=template.item_text,
                )

        serializer = InspectionSerializer(inspection)
        return Response(serializer.data)


class InspectionStartView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsInspector]

    def post(self, request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id, assigned_inspector=request.user)

        if inspection.status != Inspection.Status.SCHEDULED:
            return Response(
                {"detail": f"Cannot start inspection with status {inspection.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inspection.status = Inspection.Status.IN_PROGRESS
        inspection.start_timestamp = timezone.now()
        inspection.save(update_fields=["status", "start_timestamp"])

        return Response({
            "inspection_id": str(inspection.id),
            "status": inspection.status,
            "start_timestamp": inspection.start_timestamp.isoformat(),
        })


class InspectionChecklistUpdateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsInspector]

    def put(self, request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id, assigned_inspector=request.user)

        if inspection.status != Inspection.Status.IN_PROGRESS:
            return Response(
                {"detail": "Checklist can only be updated while inspection is in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = InspectionChecklistUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = []
        for item_data in serializer.validated_data["items"]:
            item = get_object_or_404(InspectionChecklistItem, pk=item_data["item_id"], inspection=inspection)
            if "result" in item_data:
                item.result = item_data["result"]
            if "notes" in item_data:
                item.notes = item_data.get("notes", "")
            item.save()
            updated.append(InspectionChecklistItemSerializer(item).data)

        return Response({"checklist_items": updated})


class InspectionPhotoUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsInspector]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id, assigned_inspector=request.user)

        if inspection.status != Inspection.Status.IN_PROGRESS:
            return Response(
                {"detail": "Photos can only be uploaded while inspection is in progress."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"detail": "At least one photo file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded = []
        for f in files:
            if f.size == 0:
                return Response({"detail": f"File '{f.name}' cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
            if f.size > 10 * 1024 * 1024:
                return Response({"detail": f"File '{f.name}' exceeds 10MB limit."}, status=status.HTTP_400_BAD_REQUEST)
            content_type = getattr(f, "content_type", "")
            if content_type not in ("image/jpeg", "image/png"):
                return Response({"detail": f"File '{f.name}' must be JPEG or PNG."}, status=status.HTTP_400_BAD_REQUEST)

            photo = InspectionPhoto.objects.create(inspection=inspection, file=f)
            uploaded.append(InspectionPhotoSerializer(photo).data)

        return Response({"photos": uploaded}, status=status.HTTP_201_CREATED)


class InspectionSubmitView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsInspector]

    def post(self, request, inspection_id):
        inspection = get_object_or_404(Inspection, pk=inspection_id, assigned_inspector=request.user)

        if inspection.status != Inspection.Status.IN_PROGRESS:
            return Response(
                {"detail": f"Cannot submit inspection with status {inspection.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        photo_count = inspection.photos.count()
        if photo_count < 3:
            return Response(
                {"detail": f"At least 3 photos are required before submission. Current: {photo_count}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        overall_result = request.data.get("overall_result", "").upper()
        if overall_result not in ("PASSED", "FAILED"):
            return Response(
                {"detail": "overall_result must be PASSED or FAILED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        failure_summary = request.data.get("failure_summary", "").strip()
        if overall_result == "FAILED" and len(failure_summary) < 50:
            return Response(
                {"detail": "Failure summary must be at least 50 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app = inspection.application

        with transaction.atomic():
            inspection.overall_result = overall_result
            inspection.failure_summary = failure_summary if overall_result == "FAILED" else ""
            inspection.submitted_at = timezone.now()
            inspection.status = Inspection.Status.PASSED if overall_result == "PASSED" else Inspection.Status.FAILED
            inspection.save()

            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=app.status,
                actor=request.user,
                note=f"{inspection.get_inspection_type_display()}: {overall_result}",
            )

        if overall_result == "PASSED":
            send_mail(
                subject="Inspection Passed",
                message=(
                    f"Dear {app.applicant.full_name},\n\n"
                    f"The {inspection.get_inspection_type_display()} for {app.arn} has PASSED.\n"
                    f"Submitted at: {inspection.submitted_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[app.applicant.email],
            )
            Notification.objects.create(
                recipient=app.applicant,
                title="Inspection Passed",
                body=f"{inspection.get_inspection_type_display()} for {app.arn} has passed.",
                notification_type="INSPECTION_PASSED",
                reference_id=str(inspection.id),
                reference_type="INSPECTION",
            )

            if inspection.inspection_type == Inspection.InspectionType.FOUNDATION:
                next_type = Inspection.InspectionType.STRUCTURAL_FRAME
            elif inspection.inspection_type == Inspection.InspectionType.STRUCTURAL_FRAME:
                next_type = Inspection.InspectionType.FINAL_COMPLETION
            else:
                next_type = None

            if next_type:
                existing = app.inspections.filter(
                    inspection_type=next_type, status=Inspection.Status.SCHEDULED
                ).first()
                if existing:
                    existing.status = Inspection.Status.IN_PROGRESS
                    existing.start_timestamp = timezone.now()
                    existing.save(update_fields=["status", "start_timestamp"])

        else:
            send_mail(
                subject="Inspection Failed",
                message=(
                    f"Dear {app.applicant.full_name},\n\n"
                    f"The {inspection.get_inspection_type_display()} for {app.arn} has FAILED.\n\n"
                    f"Failure Summary: {failure_summary}\n\n"
                    f"Please address the issues and request a re-inspection.\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[app.applicant.email],
            )
            Notification.objects.create(
                recipient=app.applicant,
                title="Inspection Failed",
                body=f"{inspection.get_inspection_type_display()} for {app.arn} failed: {failure_summary[:100]}.",
                notification_type="INSPECTION_FAILED",
                reference_id=str(inspection.id),
                reference_type="INSPECTION",
            )

        return Response({
            "inspection_id": str(inspection.id),
            "status": inspection.status,
            "overall_result": overall_result,
            "submitted_at": inspection.submitted_at.isoformat(),
        })


class RequestReinspectionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def post(self, request, application_id, inspection_id):
        app = get_object_or_404(Application, pk=application_id, applicant=request.user)
        original = get_object_or_404(Inspection, pk=inspection_id, application=app)

        if original.status != Inspection.Status.FAILED:
            return Response(
                {"detail": "Re-inspection can only be requested for failed inspections."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        corrections = request.data.get("corrections_made", "").strip()
        if not corrections:
            return Response(
                {"detail": "Description of corrections made is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inspector = round_robin_inspector()
        scheduled = timezone.now() + datetime.timedelta(days=14)

        with transaction.atomic():
            reinspection = Inspection.objects.create(
                application=app,
                inspection_type=Inspection.InspectionType.RE_INSPECTION,
                scheduled_date=scheduled,
                assigned_inspector=inspector,
                status=Inspection.Status.SCHEDULED,
            )

            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=app.status,
                actor=request.user,
                note=f"Re-inspection requested for {original.get_inspection_type_display()}. Corrections: {corrections}",
            )

        if inspector:
            send_mail(
                subject="Re-Inspection Scheduled",
                message=(
                    f"Dear {inspector.full_name},\n\n"
                    f"A re-inspection has been assigned to you.\n"
                    f"Application: {app.arn}\n"
                    f"Original Inspection: {original.get_inspection_type_display()}\n"
                    f"Scheduled Date: {scheduled.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Corrections Made: {corrections}\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[inspector.email],
            )
            Notification.objects.create(
                recipient=inspector,
                title="Re-Inspection Assigned",
                body=f"Re-inspection for {app.arn} scheduled on {scheduled.strftime('%Y-%m-%d')}.",
                notification_type="REINSPECTION_ASSIGNED",
                reference_id=str(reinspection.id),
                reference_type="INSPECTION",
            )

        Notification.objects.create(
            recipient=request.user,
            title="Re-Inspection Requested",
            body=f"Re-inspection requested for {app.arn}. Scheduled: {scheduled.strftime('%Y-%m-%d')}.",
            notification_type="REINSPECTION_REQUESTED",
            reference_id=str(reinspection.id),
            reference_type="INSPECTION",
        )

        return Response({
            "reinspection_id": str(reinspection.id),
            "inspection_type": reinspection.inspection_type,
            "scheduled_date": scheduled.isoformat(),
            "assigned_inspector_name": inspector.full_name if inspector else None,
            "corrections_made": corrections,
        }, status=status.HTTP_201_CREATED)
