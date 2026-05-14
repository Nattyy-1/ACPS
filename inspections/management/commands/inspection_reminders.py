from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from inspections.models import Inspection
from notifications.models import Notification


class Command(BaseCommand):
    help = "Send 48-hour pre-inspection reminder emails to inspectors and applicants"

    def handle(self, *args, **options):
        now = timezone.now()
        reminder_window_start = now + timedelta(hours=44)
        reminder_window_end = now + timedelta(hours=50)

        upcoming = Inspection.objects.filter(
            status=Inspection.Status.SCHEDULED,
            scheduled_date__gte=reminder_window_start,
            scheduled_date__lte=reminder_window_end,
        ).select_related("application", "assigned_inspector")

        notified = 0
        for inspection in upcoming:
            app = inspection.application
            inspector = inspection.assigned_inspector

            if inspector:
                send_mail(
                    subject="Upcoming Inspection Reminder (48 hours)",
                    message=(
                        f"Dear {inspector.full_name},\n\n"
                        f"This is a reminder of your upcoming inspection.\n\n"
                        f"Inspection: {inspection.get_inspection_type_display()}\n"
                        f"Application: {app.arn}\n"
                        f"Site Address: {app.plot_address}\n"
                        f"Subcity: {app.subcity_id}\n"
                        f"GPS: {app.plot_gps_lat}, {app.plot_gps_lng}\n"
                        f"Scheduled Date: {inspection.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"Thank you."
                    ),
                    from_email=None,
                    recipient_list=[inspector.email],
                )

            applicant = app.applicant
            send_mail(
                subject="Upcoming Site Inspection Reminder",
                message=(
                    f"Dear {applicant.full_name},\n\n"
                    f"This is a reminder of your upcoming site inspection.\n\n"
                    f"Inspection: {inspection.get_inspection_type_display()}\n"
                    f"Application: {app.arn}\n"
                    f"Scheduled Date: {inspection.scheduled_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"Inspector: {inspector.full_name if inspector else 'To be assigned'}\n\n"
                    f"Please ensure the site is accessible and all required documents are available.\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[applicant.email],
            )

            Notification.objects.create(
                recipient=applicant,
                title="Inspection Reminder",
                body=f"Reminder: {inspection.get_inspection_type_display()} for {app.arn} is scheduled on {inspection.scheduled_date.strftime('%Y-%m-%d')}.",
                notification_type="INSPECTION_REMINDER",
                reference_id=str(inspection.id),
                reference_type="INSPECTION",
            )

            notified += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {notified} inspection reminder(s).")
        )
