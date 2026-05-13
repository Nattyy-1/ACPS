from datetime import timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone
from payments.models import Payment
from notifications.models import Notification


class Command(BaseCommand):
    help = "Send payment reminder emails for PENDING payments older than 48 hours"

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(hours=48)
        pending = Payment.objects.filter(
            status=Payment.Status.PENDING,
            created_at__lt=cutoff,
        )
        reminded = 0
        for payment in pending:
            applicant = payment.application.applicant
            send_mail(
                subject="Payment Reminder",
                message=(
                    f"Dear {applicant.full_name},\n\n"
                    f"Your payment of ETB {float(payment.amount_etb):.2f} "
                    f"for application {payment.application.arn} is still pending.\n"
                    f"Invoice: {payment.invoice_id}\n\n"
                    f"Please complete your payment within 7 days to avoid "
                    f"automatic expiry.\n\nThank you."
                ),
                from_email=None,
                recipient_list=[applicant.email],
            )
            Notification.objects.create(
                recipient=applicant,
                title="Payment Reminder",
                body=(
                    f"Your payment of ETB {float(payment.amount_etb):.2f} "
                    f"for {payment.application.arn} is still pending."
                ),
                notification_type="PAYMENT_REMINDER",
                reference_id=str(payment.application.id),
                reference_type="APPLICATION",
            )
            reminded += 1

        self.stdout.write(
            self.style.SUCCESS(f"Sent {reminded} payment reminder(s).")
        )
