import datetime

from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin, IsApplicant, IsInspector, IsSeniorOfficer
from applications.models import Application, ApplicationHistory
from notifications.models import Notification
from .models import Inspection, InspectionChecklistTemplate, InspectionChecklistItem
from .serializers import InspectionSerializer


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
