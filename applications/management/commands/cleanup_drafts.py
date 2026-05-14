from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from django.db import transaction
from applications.models import Application, ApplicationHistory
from notifications.models import Notification


class Command(BaseCommand):
    help = "Archive DRAFT applications older than 30 days and warn at 27 days"

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff_archive = now - timedelta(days=30)
        cutoff_warn = now - timedelta(days=27)
        archived_count = 0
        warned_count = 0

        drafts = Application.objects.filter(status=Application.Status.DRAFT)

        for app in drafts:
            age = now - app.created_at

            if age >= timedelta(days=30):
                with transaction.atomic():
                    ApplicationHistory.objects.create(
                        application=app,
                        previous_status=Application.Status.DRAFT,
                        new_status=Application.Status.ARCHIVED,
                        actor=None,
                        note="Auto-archived: DRAFT older than 30 days.",
                    )
                    app.status = Application.Status.ARCHIVED
                    app.save(update_fields=["status"])
                archived_count += 1

            elif age >= timedelta(days=27):
                applicant = app.applicant
                subject = "Draft Application Expiration Warning"
                message = (
                    f"Dear {applicant.full_name},\n\n"
                    f"Your draft application ({app.arn}) is scheduled for "
                    f"automatic deletion in 3 days.\n"
                    f"Please submit or update it before it expires.\n\n"
                    f"Thank you."
                )
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=None,
                    recipient_list=[applicant.email],
                )
                Notification.objects.create(
                    recipient=applicant,
                    title="Draft Expiring Soon",
                    body=(
                        f"Your draft application ({app.arn}) will be "
                        f"auto-deleted in 3 days. Submit it now."
                    ),
                    notification_type="DRAFT_EXPIRING",
                    reference_id=str(app.id),
                    reference_type="APPLICATION",
                )
                warned_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Archived {archived_count} expired draft(s), "
                f"warned {warned_count} draft(s)."
            )
        )
