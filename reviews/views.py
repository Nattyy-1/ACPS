import datetime

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import (
    IsAdmin,
    IsAdminOrSeniorOfficer,
    IsApplicant,
    IsReviewOfficer,
    IsSeniorOfficer,
)
from applications.models import Application, ApplicationHistory, Document
from applications.serializers import ApplicationDetailSerializer
from notifications.models import Notification
from .models import ReviewComment, SLAConfig
from .serializers import (
    ReviewCommentCreateSerializer,
    ReviewCommentSerializer,
    ReviewDecisionSerializer,
    SLAConfigSerializer,
)

User = get_user_model()

REVIEW_ACTIVE_STATUSES = {
    Application.Status.AWAITING_ASSIGNMENT,
    Application.Status.REVISION_REQUIRED,
}


def round_robin_assign():
    """Assign to the REVIEW_OFFICER with fewest active reviews."""
    officers = User.objects.filter(role="REVIEW_OFFICER", is_active=True)
    if not officers:
        return None
    counts = (
        Application.objects.filter(
            assigned_officer__in=officers,
            status__in=REVIEW_ACTIVE_STATUSES,
        )
        .values("assigned_officer")
        .annotate(count=Count("id"))
    )
    count_map = {str(c["assigned_officer"]): c["count"] for c in counts}
    best = min(officers, key=lambda o: count_map.get(str(o.id), 0))
    return best


class AssignReviewerView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.AWAITING_ASSIGNMENT:
            return Response(
                {
                    "detail": f"Cannot assign reviewer when status is {app.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        officer_id = request.data.get("officer_id")
        if officer_id:
            try:
                officer = User.objects.get(
                    pk=officer_id, role="REVIEW_OFFICER", is_active=True
                )
            except User.DoesNotExist:
                return Response(
                    {"detail": "Review officer not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            officer = round_robin_assign()
            if not officer:
                return Response(
                    {"detail": "No available review officers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.AWAITING_ASSIGNMENT,
                actor=request.user,
                note=f"Assigned to reviewer {officer.full_name}.",
            )
            app.assigned_officer = officer
            app.save(update_fields=["assigned_officer"])

        Notification.objects.create(
            recipient=officer,
            title="New Application Assigned",
            body=f"Application {app.arn} has been assigned to you for review.",
            notification_type="ASSIGNMENT",
            reference_id=str(app.id),
            reference_type="APPLICATION",
        )

        return Response(
            {
                "application_id": str(app.id),
                "arn": app.arn,
                "assigned_officer": {
                    "id": str(officer.id),
                    "full_name": officer.full_name,
                },
            }
        )


class ReviewQueueView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsReviewOfficer]

    def get(self, request):
        qs = Application.objects.filter(
            assigned_officer=request.user,
            status__in=REVIEW_ACTIVE_STATUSES,
        ).order_by("created_at")

        results = []
        for app in qs:
            sla = SLAConfig.objects.filter(stage="technical_review").first()
            days_open = (datetime.date.today() - app.created_at.date()).days
            urgency = "normal"
            if sla and days_open >= sla.escalation_days:
                urgency = "critical"
            elif sla and days_open >= sla.reminder_days:
                urgency = "warning"

            results.append(
                {
                    "application_id": str(app.id),
                    "arn": app.arn,
                    "status": app.status,
                    "building_category": app.building_category,
                    "subcity_id": app.subcity_id,
                    "created_at": app.created_at.isoformat(),
                    "days_open": days_open,
                    "urgency": urgency,
                    "revision_cycle": app.revision_cycle,
                }
            )

        return Response(results)


class ReviewWorkspaceView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsReviewOfficer]

    def get(self, request, application_id):
        try:
            app = Application.objects.get(
                pk=application_id, assigned_officer=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ApplicationDetailSerializer(app)
        return Response(serializer.data)


class CommentView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsReviewOfficer]

    def post(self, request, application_id):
        try:
            app = Application.objects.get(
                pk=application_id, assigned_officer=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ReviewCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.save(application=app, author=request.user)

        with transaction.atomic():
            if app.status != Application.Status.REVISION_REQUIRED:
                ApplicationHistory.objects.create(
                    application=app,
                    previous_status=app.status,
                    new_status=Application.Status.REVISION_REQUIRED,
                    actor=request.user,
                    note="Reviewer requested revision.",
                )
                app.status = Application.Status.REVISION_REQUIRED
                app.revision_cycle += 1
                app.save(update_fields=["status", "revision_cycle"])

                applicant = app.applicant
                send_mail(
                    subject="Revision Required",
                    message=(
                        f"Dear {applicant.full_name},\n\n"
                        f"Application {app.arn} requires revision. "
                        f"The reviewer has left {app.review_comments.count()} "
                        f"comment(s).\n"
                        f"Please log in to view and address them."
                    ),
                    from_email=None,
                    recipient_list=[applicant.email],
                )
                Notification.objects.create(
                    recipient=applicant,
                    title="Revision Required",
                    body=f"Application {app.arn} requires revision.",
                    notification_type="REVISION_REQUIRED",
                    reference_id=str(app.id),
                    reference_type="APPLICATION",
                )

            if app.revision_cycle > 3:
                seniors = User.objects.filter(
                    role="SENIOR_OFFICER", is_active=True
                )
                for senior in seniors:
                    Notification.objects.create(
                        recipient=senior,
                        title="Excessive Revision Cycles",
                        body=(
                            f"Application {app.arn} has exceeded 3 revision "
                            f"cycles ({app.revision_cycle})."
                        ),
                        notification_type="EXCESS_REVISIONS",
                        reference_id=str(app.id),
                        reference_type="APPLICATION",
                    )

        return Response(
            ReviewCommentSerializer(comment).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        user = request.user
        if user.role == "APPLICANT" and app.applicant != user:
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if user.role == "REVIEW_OFFICER" and app.assigned_officer != user:
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        comments = app.review_comments.all().order_by("-created_at")
        serializer = ReviewCommentSerializer(comments, many=True)
        return Response(serializer.data)


class CommentResolveView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsReviewOfficer]

    def put(self, request, application_id, comment_id):
        try:
            app = Application.objects.get(
                pk=application_id, assigned_officer=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            comment = ReviewComment.objects.get(pk=comment_id, application=app)
        except ReviewComment.DoesNotExist:
            return Response(
                {"detail": "Comment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        resolution = request.data.get("resolution_status", "RESOLVED")
        if resolution not in ("RESOLVED", "ESCALATED"):
            return Response(
                {"detail": "resolution_status must be RESOLVED or ESCALATED."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        comment.resolution_status = resolution
        comment.resolved_by = request.user
        comment.resolved_at = datetime.datetime.now()
        comment.save()
        return Response(ReviewCommentSerializer(comment).data)


class ReviewDecisionView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsReviewOfficer]

    def post(self, request, application_id):
        try:
            app = Application.objects.get(
                pk=application_id, assigned_officer=request.user
            )
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found or not assigned to you."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        notes = serializer.validated_data.get("notes", "")
        citation = serializer.validated_data.get("regulation_citation", "")

        with transaction.atomic():
            if decision == "APPROVED":
                ApplicationHistory.objects.create(
                    application=app,
                    previous_status=app.status,
                    new_status=Application.Status.AWAITING_SENIOR_APPROVAL,
                    actor=request.user,
                    note="Reviewer approved application.",
                )
                app.status = Application.Status.AWAITING_SENIOR_APPROVAL
                app.save(update_fields=["status"])

                seniors = User.objects.filter(
                    role="SENIOR_OFFICER", is_active=True
                )
                for senior in seniors:
                    Notification.objects.create(
                        recipient=senior,
                        title="Application Awaiting Approval",
                        body=f"Application {app.arn} has been approved by reviewer and awaits your decision.",
                        notification_type="AWAITING_SENIOR_APPROVAL",
                        reference_id=str(app.id),
                        reference_type="APPLICATION",
                    )
                return Response(
                    {
                        "decision": "APPROVED",
                        "status": app.status,
                        "message": "Application approved. Awaiting senior officer approval.",
                    }
                )

            else:
                ApplicationHistory.objects.create(
                    application=app,
                    previous_status=app.status,
                    new_status=Application.Status.REJECTED,
                    actor=request.user,
                    note=f"Rejected: {notes}",
                )
                app.status = Application.Status.REJECTED
                app.save(update_fields=["status"])

                applicant = app.applicant
                send_mail(
                    subject="Application Rejected",
                    message=(
                        f"Dear {applicant.full_name},\n\n"
                        f"Your application {app.arn} has been rejected.\n\n"
                        f"Reason: {notes}\n"
                        f"Regulation: {citation}\n\n"
                        f"Thank you."
                    ),
                    from_email=None,
                    recipient_list=[applicant.email],
                )
                Notification.objects.create(
                    recipient=applicant,
                    title="Application Rejected",
                    body=f"Your application {app.arn} has been rejected.",
                    notification_type="REJECTED",
                    reference_id=str(app.id),
                    reference_type="APPLICATION",
                )
                return Response(
                    {
                        "decision": "REJECTED",
                        "status": app.status,
                        "message": "Application rejected.",
                    }
                )


class SLAStatusView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdminOrSeniorOfficer]

    def get(self, request):
        configs = SLAConfig.objects.all()
        sla_data = SLAConfigSerializer(configs, many=True).data

        apps = Application.objects.filter(
            status__in=REVIEW_ACTIVE_STATUSES
        ).select_related("assigned_officer")

        breaches = []
        for app in apps:
            sla = SLAConfig.objects.filter(stage="technical_review").first()
            if not sla:
                continue
            days_open = (datetime.date.today() - app.created_at.date()).days
            if days_open >= sla.target_days:
                breaches.append(
                    {
                        "application_id": str(app.id),
                        "arn": app.arn,
                        "status": app.status,
                        "assigned_officer": app.assigned_officer.full_name
                        if app.assigned_officer
                        else "Unassigned",
                        "days_open": days_open,
                        "target_days": sla.target_days,
                        "breached": days_open >= sla.target_days,
                    }
                )

        return Response(
            {
                "sla_configs": sla_data,
                "breaches": breaches,
                "breach_count": len(breaches),
            }
        )
