import csv
import datetime

from django.http import HttpResponse
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin
from applications.models import Application, ApplicationHistory
from inspections.models import Inspection, InspectionChecklistTemplate
from notifications.services import EVENT_EMAIL_TEMPLATES
from payments.models import FeeSchedule, Payment
from reviews.models import SLAConfig
from .models import NotificationTemplate


class AdminStatsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        total_apps = Application.objects.count()
        apps_by_status = (
            Application.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )

        avg_days_per_stage = {}
        for status_choice in [
            "DRAFT", "PAYMENT_PENDING", "AWAITING_ASSIGNMENT",
            "REVISION_REQUIRED", "AWAITING_SENIOR_APPROVAL",
            "CONSENT_ISSUED", "PERMIT_ISSUED", "UNDER_CONSTRUCTION",
            "COMPLETION_DECLARED", "COMPLETED", "REJECTED",
        ]:
            apps = Application.objects.filter(status=status_choice)
            if apps.exists():
                total_days = 0
                count = 0
                for app in apps:
                    days = (timezone.now().date() - app.created_at.date()).days
                    total_days += max(days, 0)
                    count += 1
                avg_days_per_stage[status_choice] = round(total_days / count, 1) if count else 0
            else:
                avg_days_per_stage[status_choice] = 0

        sla_breaches = Application.objects.filter(
            status__in=["AWAITING_ASSIGNMENT", "REVISION_REQUIRED"]
        ).count()

        payment_stats = Payment.objects.aggregate(
            total_volume=Sum("amount_etb", filter=Q(status="CONFIRMED")),
            total_count=Count("id", filter=Q(status="CONFIRMED")),
            pending_count=Count("id", filter=Q(status="PENDING")),
        )

        recent_inspections = Inspection.objects.filter(
            status__in=["PASSED", "FAILED"]
        ).count()

        return Response({
            "total_applications": total_apps,
            "applications_by_status": list(apps_by_status),
            "average_days_per_stage": avg_days_per_stage,
            "sla_breach_count": sla_breaches,
            "payment_volume": {
                "total_etb": float(payment_stats["total_volume"] or 0),
                "total_confirmed": payment_stats["total_count"] or 0,
                "pending_count": payment_stats["pending_count"] or 0,
            },
            "completed_inspections": recent_inspections,
        })


class AuditLogView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = ApplicationHistory.objects.all().select_related("actor", "application")

        user_id = request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(actor_id=user_id)

        action_type = request.query_params.get("action_type")
        if action_type:
            qs = qs.filter(new_status=action_type.upper())

        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__gte=date_from)

        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__lte=date_to)

        qs = qs.order_by("-created_at")

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()
        results = qs[start:end]

        return Response({
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": [
                {
                    "history_id": str(h.id),
                    "application_id": str(h.application.id),
                    "arn": h.application.arn,
                    "previous_status": h.previous_status,
                    "new_status": h.new_status,
                    "actor_name": h.actor.full_name if h.actor else "System",
                    "actor_id": str(h.actor.id) if h.actor else None,
                    "note": h.note,
                    "created_at": h.created_at.isoformat(),
                }
                for h in results
            ],
        })


class FeeScheduleConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        tiers = FeeSchedule.objects.all().order_by("min_value_etb")
        return Response([
            {
                "id": str(t.id),
                "min_value_etb": float(t.min_value_etb),
                "max_value_etb": float(t.max_value_etb) if t.max_value_etb else None,
                "fee_percentage": float(t.fee_percentage),
                "fixed_fee_etb": float(t.fixed_fee_etb),
            }
            for t in tiers
        ])

    def put(self, request):
        tiers = request.data.get("tiers", [])
        if not isinstance(tiers, list):
            return Response({"detail": "tiers must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        FeeSchedule.objects.all().delete()
        for tier in tiers:
            FeeSchedule.objects.create(
                min_value_etb=tier["min_value_etb"],
                max_value_etb=tier.get("max_value_etb"),
                fee_percentage=tier["fee_percentage"],
                fixed_fee_etb=tier.get("fixed_fee_etb", 0),
            )

        return Response({"detail": f"{len(tiers)} fee tier(s) updated."})


class SLAConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        configs = SLAConfig.objects.all()
        return Response([
            {
                "id": str(c.id),
                "stage": c.stage,
                "target_days": c.target_days,
                "reminder_days": c.reminder_days,
                "escalation_days": c.escalation_days,
            }
            for c in configs
        ])

    def put(self, request):
        configs = request.data.get("configs", [])
        if not isinstance(configs, list):
            return Response({"detail": "configs must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        SLAConfig.objects.all().delete()
        for cfg in configs:
            SLAConfig.objects.create(
                stage=cfg["stage"],
                target_days=cfg["target_days"],
                reminder_days=cfg["reminder_days"],
                escalation_days=cfg["escalation_days"],
            )

        return Response({"detail": f"{len(configs)} SLA config(s) updated."})


class InspectionChecklistConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, inspection_type):
        items = InspectionChecklistTemplate.objects.filter(
            inspection_type=inspection_type.upper(), is_active=True
        ).order_by("order")

        return Response([
            {
                "id": str(i.id),
                "inspection_type": i.inspection_type,
                "item_text": i.item_text,
                "order": i.order,
            }
            for i in items
        ])

    def put(self, request, inspection_type):
        items = request.data.get("items", [])
        if not isinstance(items, list):
            return Response({"detail": "items must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        InspectionChecklistTemplate.objects.filter(
            inspection_type=inspection_type.upper()
        ).update(is_active=False)

        for idx, item in enumerate(items):
            InspectionChecklistTemplate.objects.create(
                inspection_type=inspection_type.upper(),
                item_text=item["item_text"],
                order=item.get("order", idx + 1),
                is_active=True,
            )

        return Response({"detail": f"{len(items)} checklist item(s) updated for {inspection_type}."})


class NotificationTemplateConfigView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        db_templates = {
            t.notification_type: t for t in NotificationTemplate.objects.all()
        }
        all_types = set(EVENT_EMAIL_TEMPLATES.keys()) | set(db_templates.keys())

        results = []
        for ntype in sorted(all_types):
            if ntype in db_templates:
                t = db_templates[ntype]
                results.append({
                    "id": str(t.id),
                    "notification_type": t.notification_type,
                    "subject": t.subject,
                    "body": t.body,
                })
            else:
                template = EVENT_EMAIL_TEMPLATES.get(ntype, {})
                results.append({
                    "id": None,
                    "notification_type": ntype,
                    "subject": template.get("subject", ""),
                    "body": template.get("body", ""),
                })

        return Response(results)

    def post(self, request):
        ntype = request.data.get("notification_type", "").strip()
        subject = request.data.get("subject", "").strip()
        body = request.data.get("body", "").strip()

        if not all([ntype, subject, body]):
            return Response(
                {"detail": "notification_type, subject, and body are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template, created = NotificationTemplate.objects.update_or_create(
            notification_type=ntype,
            defaults={"subject": subject, "body": body},
        )

        return Response({
            "detail": "Template created." if created else "Template updated.",
            "notification_type": template.notification_type,
        })


class ReportsExportView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        report_type = request.query_params.get("report_type", "applications")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{report_type}_{datetime.date.today()}.csv"'
        writer = csv.writer(response)

        if report_type == "applications":
            writer.writerow(["ARN", "Status", "Category", "Applicant", "Subcity", "Created", "Fee", "Project Value"])
            qs = Application.objects.all().select_related("applicant")
            if date_from:
                qs = qs.filter(created_at__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__lte=date_to)
            for app in qs:
                writer.writerow([
                    app.arn, app.status, app.building_category,
                    app.applicant.full_name, app.subcity_id,
                    app.created_at.date(), float(app.calculated_fee or 0),
                    float(app.project_value_etb),
                ])

        elif report_type == "payments":
            writer.writerow(["Invoice", "ARN", "Amount", "Method", "Status", "Paid At", "Transaction"])
            qs = Payment.objects.all().select_related("application")
            if date_from:
                qs = qs.filter(created_at__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__lte=date_to)
            for p in qs:
                writer.writerow([
                    p.invoice_id, p.application.arn, float(p.amount_etb),
                    p.payment_method, p.status,
                    p.paid_at.date() if p.paid_at else "",
                    p.transaction_reference,
                ])

        elif report_type == "inspections":
            writer.writerow(["ID", "ARN", "Type", "Status", "Result", "Inspector", "Scheduled", "Submitted"])
            qs = Inspection.objects.all().select_related("application", "assigned_inspector")
            if date_from:
                qs = qs.filter(created_at__gte=date_from)
            if date_to:
                qs = qs.filter(created_at__lte=date_to)
            for i in qs:
                writer.writerow([
                    i.id, i.application.arn, i.inspection_type, i.status,
                    i.overall_result,
                    i.assigned_inspector.full_name if i.assigned_inspector else "",
                    i.scheduled_date.date(),
                    i.submitted_at.date() if i.submitted_at else "",
                ])

        else:
            return Response(
                {"detail": "Invalid report_type. Use: applications, payments, inspections."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return response
