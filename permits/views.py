import datetime
import io

from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin, IsAdminOrSeniorOfficer, IsApplicant, IsSeniorOfficer
from applications.models import Application, ApplicationHistory, Document
from notifications.models import Notification
from .models import Permit
from .pdf_utils import generate_planning_consent_pdf, generate_construction_permit_pdf
from .serializers import AuthenticatedPermitSerializer, PublicPermitSerializer


class ApprovalsQueueView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSeniorOfficer]

    def get(self, request):
        qs = Application.objects.filter(
            status=Application.Status.AWAITING_SENIOR_APPROVAL
        ).order_by("updated_at")

        results = []
        for app in qs:
            reviewer_decision = (
                app.history.filter(new_status__in=["AWAITING_SENIOR_APPROVAL", "REVISION_REQUIRED"])
                .order_by("-created_at")
                .first()
            )
            comments_count = app.review_comments.count()
            unresolved = app.review_comments.filter(
                resolution_status__in=["OPEN", "ESCALATED"]
            ).count()

            results.append({
                "application_id": str(app.id),
                "arn": app.arn,
                "applicant_name": app.applicant.full_name,
                "building_category": app.building_category,
                "subcity_id": app.subcity_id,
                "status": app.status,
                "revision_cycle": app.revision_cycle,
                "comments_count": comments_count,
                "unresolved_comments": unresolved,
                "assigned_reviewer": app.assigned_officer.full_name if app.assigned_officer else None,
                "created_at": app.created_at.isoformat(),
                "updated_at": app.updated_at.isoformat(),
            })

        return Response(results)


class ApprovalDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSeniorOfficer]

    def get(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id)

        docs = app.documents.filter(is_current=True)
        comments = app.review_comments.all().order_by("-created_at")
        history = app.history.all().order_by("-created_at")

        return Response({
            "application_id": str(app.id),
            "arn": app.arn,
            "applicant": {
                "id": str(app.applicant.id),
                "full_name": app.applicant.full_name,
                "email": app.applicant.email,
                "phone": app.applicant.phone,
            },
            "building_category": app.building_category,
            "status": app.status,
            "subcity_id": app.subcity_id,
            "woreda": app.woreda,
            "plot_address": app.plot_address,
            "plot_gps_lat": float(app.plot_gps_lat),
            "plot_gps_lng": float(app.plot_gps_lng),
            "height_m": float(app.height_m),
            "floors_above": app.floors_above,
            "floors_below": app.floors_below,
            "floor_area_sqm": float(app.floor_area_sqm),
            "intended_use": app.intended_use,
            "architect_name": app.architect_name,
            "architect_license": app.architect_license,
            "project_value_etb": float(app.project_value_etb),
            "calculated_fee": float(app.calculated_fee) if app.calculated_fee else None,
            "revision_cycle": app.revision_cycle,
            "assigned_reviewer": {
                "id": str(app.assigned_officer.id),
                "full_name": app.assigned_officer.full_name,
            } if app.assigned_officer else None,
            "documents": [
                {
                    "document_id": str(d.id),
                    "document_type": d.document_type,
                    "file_name": d.file_name,
                    "validation_status": d.validation_status,
                    "version_number": d.version_number,
                }
                for d in docs
            ],
            "comments": [
                {
                    "comment_id": str(c.id),
                    "category": c.category,
                    "content": c.content,
                    "author_name": c.author.full_name if c.author else "Unknown",
                    "resolution_status": c.resolution_status,
                    "resolved_at": c.resolved_at.isoformat() if c.resolved_at else None,
                    "created_at": c.created_at.isoformat(),
                }
                for c in comments
            ],
            "history": [
                {
                    "previous_status": h.previous_status,
                    "new_status": h.new_status,
                    "note": h.note,
                    "actor_name": h.actor.full_name if h.actor else "System",
                    "created_at": h.created_at.isoformat(),
                }
                for h in history
            ],
            "created_at": app.created_at.isoformat(),
            "updated_at": app.updated_at.isoformat(),
        })


class IssueConsentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSeniorOfficer]

    def post(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id)

        if app.status != Application.Status.AWAITING_SENIOR_APPROVAL:
            return Response(
                {"detail": f"Cannot issue consent when status is {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = datetime.date.today().year
        prefix = f"PC-{year}-"
        last = Permit.objects.filter(
            permit_number__startswith=prefix, permit_type=Permit.PermitType.PLANNING_CONSENT
        ).order_by("permit_number").last()
        next_num = int(last.permit_number.split("-")[-1]) + 1 if last else 1
        permit_number = f"{prefix}{next_num:06d}"
        issue_date = datetime.date.today()
        expiry_date = issue_date + datetime.timedelta(days=180)

        qr_token = permit_number.replace("-", "").lower()
        verify_url = f"{request.build_absolute_uri('/')[:-1]}/api/v1/verify/{permit_number}/"

        with transaction.atomic():
            permit = Permit.objects.create(
                application=app,
                permit_number=permit_number,
                permit_type=Permit.PermitType.PLANNING_CONSENT,
                issued_by=request.user,
                issue_date=issue_date,
                expiry_date=expiry_date,
                qr_code_token=qr_token,
                status=Permit.Status.ACTIVE,
            )

            pdf_buf = generate_planning_consent_pdf(app, permit, verify_url)
            file_name = f"planning_consent_{permit_number}.pdf"

            permit.document_path.save(file_name, pdf_buf, save=True)

            Document.objects.create(
                application=app,
                uploader=request.user,
                document_type=Document.DocumentType.CONSENT,
                file_path=permit.document_path,
                file_name=file_name,
                file_size_bytes=pdf_buf.tell(),
                mime_type="application/pdf",
                validation_status=Document.ValidationStatus.ACCEPTED,
                is_current=True,
            )

            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.CONSENT_ISSUED,
                actor=request.user,
                note=f"Planning consent {permit_number} issued.",
            )
            app.status = Application.Status.CONSENT_ISSUED
            app.save(update_fields=["status"])

        send_mail(
            subject="Planning Consent Issued",
            message=(
                f"Dear {app.applicant.full_name},\n\n"
                f"Planning consent has been issued for your application {app.arn}.\n"
                f"Permit Number: {permit_number}\n"
                f"Valid until: {expiry_date.strftime('%Y-%m-%d')}\n\n"
                f"Please log in to download the PDF.\n\n"
                f"Thank you."
            ),
            from_email=None,
            recipient_list=[app.applicant.email],
        )

        Notification.objects.create(
            recipient=app.applicant,
            title="Planning Consent Issued",
            body=f"Planning consent {permit_number} issued for {app.arn}.",
            notification_type="CONSENT_ISSUED",
            reference_id=str(app.id),
            reference_type="APPLICATION",
        )

        return Response({
            "permit_number": permit_number,
            "permit_type": "PLANNING_CONSENT",
            "issue_date": issue_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "application_status": app.status,
            "document_url": permit.document_path.url if permit.document_path else None,
        }, status=status.HTTP_201_CREATED)


class IssuePermitView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSeniorOfficer]

    def post(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id)

        if app.status not in (Application.Status.CONSENT_ISSUED, Application.Status.AWAITING_SENIOR_APPROVAL):
            return Response(
                {"detail": f"Cannot issue construction permit when status is {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not app.contractor_name:
            return Response(
                {"detail": "Contractor name must be set before issuing a construction permit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        year = datetime.date.today().year
        prefix = f"CP-{year}-"
        last = Permit.objects.filter(
            permit_number__startswith=prefix, permit_type=Permit.PermitType.CONSTRUCTION
        ).order_by("permit_number").last()
        next_num = int(last.permit_number.split("-")[-1]) + 1 if last else 1
        permit_number = f"{prefix}{next_num:06d}"
        issue_date = datetime.date.today()
        expiry_date = issue_date + datetime.timedelta(days=365)

        qr_token = permit_number.replace("-", "").lower()
        verify_url = f"{request.build_absolute_uri('/')[:-1]}/api/v1/verify/{permit_number}/"

        with transaction.atomic():
            permit = Permit.objects.create(
                application=app,
                permit_number=permit_number,
                permit_type=Permit.PermitType.CONSTRUCTION,
                issued_by=request.user,
                issue_date=issue_date,
                expiry_date=expiry_date,
                qr_code_token=qr_token,
                status=Permit.Status.ACTIVE,
            )

            pdf_buf = generate_construction_permit_pdf(app, permit, verify_url)
            file_name = f"construction_permit_{permit_number}.pdf"

            permit.document_path.save(file_name, pdf_buf, save=True)

            Document.objects.create(
                application=app,
                uploader=request.user,
                document_type=Document.DocumentType.PERMIT,
                file_path=permit.document_path,
                file_name=file_name,
                file_size_bytes=pdf_buf.tell(),
                mime_type="application/pdf",
                validation_status=Document.ValidationStatus.ACCEPTED,
                is_current=True,
            )

            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.PERMIT_ISSUED,
                actor=request.user,
                note=f"Construction permit {permit_number} issued.",
            )
            app.status = Application.Status.PERMIT_ISSUED
            app.save(update_fields=["status"])

        send_mail(
            subject="Construction Permit Issued",
            message=(
                f"Dear {app.applicant.full_name},\n\n"
                f"A construction permit has been issued for your application {app.arn}.\n"
                f"Permit Number: {permit_number}\n"
                f"Valid until: {expiry_date.strftime('%Y-%m-%d')}\n\n"
                f"Please log in to download the PDF.\n\n"
                f"Thank you."
            ),
            from_email=None,
            recipient_list=[app.applicant.email],
        )

        Notification.objects.create(
            recipient=app.applicant,
            title="Construction Permit Issued",
            body=f"Construction permit {permit_number} issued for {app.arn}.",
            notification_type="PERMIT_ISSUED",
            reference_id=str(app.id),
            reference_type="APPLICATION",
        )

        return Response({
            "permit_number": permit_number,
            "permit_type": "CONSTRUCTION",
            "issue_date": issue_date.isoformat(),
            "expiry_date": expiry_date.isoformat(),
            "application_status": app.status,
            "document_url": permit.document_path.url if permit.document_path else None,
        }, status=status.HTTP_201_CREATED)


class SeniorRejectView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSeniorOfficer]

    def post(self, request, application_id):
        app = get_object_or_404(Application, pk=application_id)

        if app.status != Application.Status.AWAITING_SENIOR_APPROVAL:
            return Response(
                {"detail": f"Cannot reject when status is {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get("reason", "").strip()
        citation = request.data.get("regulation_citation", "").strip()

        if len(reason) < 100:
            return Response(
                {"detail": "Reason must be at least 100 characters for rejection."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not citation:
            return Response(
                {"detail": "Regulation citation is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.REJECTED,
                actor=request.user,
                note=f"Final rejection: {reason} (Regulation: {citation})",
            )
            app.status = Application.Status.REJECTED
            app.save(update_fields=["status"])

        send_mail(
            subject="Application Rejected",
            message=(
                f"Dear {app.applicant.full_name},\n\n"
                f"Your application {app.arn} has been rejected at the final stage.\n\n"
                f"Reason: {reason}\n"
                f"Regulation: {citation}\n\n"
                f"Thank you."
            ),
            from_email=None,
            recipient_list=[app.applicant.email],
        )

        Notification.objects.create(
            recipient=app.applicant,
            title="Application Rejected",
            body=f"Your application {app.arn} has been finally rejected.",
            notification_type="REJECTED",
            reference_id=str(app.id),
            reference_type="APPLICATION",
        )

        return Response({
            "status": app.status,
            "message": "Application rejected at final stage.",
        })


class PermitDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        return [] if self.request.method == "GET" and not self.request.user.is_authenticated else [IsAuthenticated()]

    def get(self, request, permit_number):
        permit = get_object_or_404(Permit, permit_number=permit_number)
        if request.user.is_authenticated:
            serializer = AuthenticatedPermitSerializer(permit)
        else:
            serializer = PublicPermitSerializer(permit)
        return Response(serializer.data)


def permit_verify_view(request, permit_number):
    try:
        permit = Permit.objects.get(permit_number=permit_number)
        context = {
            "valid": permit.status == Permit.Status.ACTIVE,
            "permit_number": permit.permit_number,
            "permit_type": permit.get_permit_type_display(),
            "issue_date": permit.issue_date,
            "expiry_date": permit.expiry_date,
            "status": permit.get_status_display(),
            "applicant_name": permit.application.applicant.full_name,
            "plot_address": permit.application.plot_address,
        }
    except Permit.DoesNotExist:
        context = {
            "valid": False,
            "permit_number": permit_number,
            "error": "Permit not found.",
        }
    return render(request, "permits/verify.html", context)
