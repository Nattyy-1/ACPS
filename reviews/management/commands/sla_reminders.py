import datetime
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.db.models import Count
from django.utils import timezone
from applications.models import Application
from notifications.models import Notification
from reviews.models import SLAConfig

REVIEW_ACTIVE_STATUSES = {
    Application.Status.AWAITING_ASSIGNMENT,
    Application.Status.REVISION_REQUIRED,
}


class Command(BaseCommand):
    help = "Send SLA reminder/escalation emails for overdue reviews"

    def handle(self, *args, **options):
        sla = SLAConfig.objects.filter(stage="technical_review").first()
        if not sla:
            self.stdout.write(self.style.WARNING("No SLA config found for technical_review."))
            return

        now = datetime.date.today()
        apps = Application.objects.filter(status__in=REVIEW_ACTIVE_STATUSES)
        reminded = 0
        escalated = 0

        for app in apps:
            days_open = (now - app.created_at.date()).days

            if days_open >= sla.escalation_days and days_open < sla.escalation_days + 1:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                seniors = User.objects.filter(role="SENIOR_OFFICER", is_active=True)
                admins = User.objects.filter(role="ADMIN", is_active=True)
                for recipient in list(seniors) + list(admins):
                    send_mail(
                        subject="SLA Breach: Review Overdue",
                        message=(
                            f"Application {app.arn} has been in review for {days_open} days "
                            f"(target: {sla.target_days} days).\n"
                            f"Reviewer: {app.assigned_officer.full_name if app.assigned_officer else 'Unassigned'}\n"
                            f"Status: {app.status}\n\n"
                            f"Immediate attention required."
                        ),
                        from_email=None,
                        recipient_list=[recipient.email],
                    )
                    Notification.objects.create(
                        recipient=recipient,
                        title="SLA Breach: Review Overdue",
                        body=f"Application {app.arn} has exceeded {sla.escalation_days} days in review.",
                        notification_type="SLA_BREACH",
                        reference_id=str(app.id),
                        reference_type="APPLICATION",
                    )
                escalated += 1

            elif days_open >= sla.reminder_days and days_open < sla.reminder_days + 1:
                if app.assigned_officer:
                    send_mail(
                        subject="Review Reminder",
                        message=(
                            f"Dear {app.assigned_officer.full_name},\n\n"
                            f"Application {app.arn} has been in review for {days_open} days "
                            f"(target: {sla.target_days} days).\n"
                            f"Please complete your review as soon as possible.\n\n"
                            f"Thank you."
                        ),
                        from_email=None,
                        recipient_list=[app.assigned_officer.email],
                    )
                    Notification.objects.create(
                        recipient=app.assigned_officer,
                        title="Review Reminder",
                        body=f"Application {app.arn} has been in review for {days_open} days.",
                        notification_type="REVIEW_REMINDER",
                        reference_id=str(app.id),
                        reference_type="APPLICATION",
                    )
                reminded += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent {reminded} reminder(s) and {escalated} escalation(s)."
            )
        )
