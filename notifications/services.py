from django.core.mail import send_mail
from .models import Notification


def create_notification(recipient, title, body, notification_type, reference_id="", reference_type=""):
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        notification_type=notification_type,
        reference_id=str(reference_id) if reference_id else "",
        reference_type=reference_type,
    )


EVENT_EMAIL_TEMPLATES = {
    "REGISTRATION": {
        "subject": "Welcome to the Building Permit System",
        "body": (
            "Dear {full_name},\n\n"
            "Your account has been created successfully.\n"
            "You can now log in and submit building permit applications.\n\n"
            "Thank you."
        ),
    },
    "SUBMISSION": {
        "subject": "Application Submitted",
        "body": (
            "Dear {full_name},\n\n"
            "Your application {arn} has been submitted successfully.\n"
            "Please proceed with payment to continue the process.\n\n"
            "Thank you."
        ),
    },
    "PAYMENT_CONFIRMED": {
        "subject": "Payment Confirmed",
        "body": (
            "Dear {full_name},\n\n"
            "Your payment of ETB {amount:.2f} for {arn} has been confirmed.\n"
            "Transaction: {transaction_ref}\n\n"
            "Thank you."
        ),
    },
    "ASSIGNMENT": {
        "subject": "New Application Assigned",
        "body": (
            "Dear {full_name},\n\n"
            "Application {arn} has been assigned to you for review.\n\n"
            "Thank you."
        ),
    },
    "REVISION_REQUIRED": {
        "subject": "Revision Required",
        "body": (
            "Dear {full_name},\n\n"
            "Application {arn} requires revision. "
            "The reviewer has left {comment_count} comment(s).\n"
            "Please log in to view and address them."
        ),
    },
    "APPROVED": {
        "subject": "Application Approved",
        "body": (
            "Dear {full_name},\n\n"
            "Your application {arn} has been approved by the reviewer. "
            "It now awaits senior officer approval.\n\n"
            "Thank you."
        ),
    },
    "REJECTED": {
        "subject": "Application Rejected",
        "body": (
            "Dear {full_name},\n\n"
            "Your application {arn} has been rejected.\n"
            "Reason: {reason}\n\n"
            "Thank you."
        ),
    },
    "CONSENT_ISSUED": {
        "subject": "Planning Consent Issued",
        "body": (
            "Dear {full_name},\n\n"
            "Planning consent has been issued for {arn}.\n"
            "Permit: {permit_number}\n"
            "Valid until: {expiry_date}\n\n"
            "Please log in to download the PDF.\n\n"
            "Thank you."
        ),
    },
    "PERMIT_ISSUED": {
        "subject": "Construction Permit Issued",
        "body": (
            "Dear {full_name},\n\n"
            "A construction permit has been issued for {arn}.\n"
            "Permit: {permit_number}\n"
            "Valid until: {expiry_date}\n\n"
            "Please log in to download the PDF.\n\n"
            "Thank you."
        ),
    },
    "CERTIFICATE_ISSUED": {
        "subject": "Completion Certificate Issued",
        "body": (
            "Dear {full_name},\n\n"
            "Your completion certificate has been issued for {arn}.\n"
            "Certificate: {permit_number}\n\n"
            "Congratulations on completing your project!\n\n"
            "Thank you."
        ),
    },
    "INSPECTION_ASSIGNED": {
        "subject": "Inspection Scheduled",
        "body": (
            "Dear {full_name},\n\n"
            "A {inspection_type} has been scheduled for {arn}.\n"
            "Date: {scheduled_date}\n"
            "Site: {plot_address}\n\n"
            "Thank you."
        ),
    },
    "INSPECTION_PASSED": {
        "subject": "Inspection Passed",
        "body": (
            "Dear {full_name},\n\n"
            "The {inspection_type} for {arn} has PASSED.\n\n"
            "Thank you."
        ),
    },
    "INSPECTION_FAILED": {
        "subject": "Inspection Failed",
        "body": (
            "Dear {full_name},\n\n"
            "The {inspection_type} for {arn} has FAILED.\n\n"
            "Summary: {failure_summary}\n\n"
            "Please address the issues and request a re-inspection.\n\n"
            "Thank you."
        ),
    },
    "REVIEW_REMINDER": {
        "subject": "Review Reminder",
        "body": (
            "Dear {full_name},\n\n"
            "Application {arn} has been in review for {days_open} days "
            "(target: {target_days} days).\n"
            "Please complete your review.\n\n"
            "Thank you."
        ),
    },
    "SLA_BREACH": {
        "subject": "SLA Breach: Review Overdue",
        "body": (
            "Application {arn} has been in review for {days_open} days "
            "(target: {target_days} days).\n"
            "Reviewer: {reviewer}\n"
            "Status: {status}\n\n"
            "Immediate attention required."
        ),
    },
}


def send_notification_email(notification_type, recipient_email, context=None):
    if context is None:
        context = {}
    template = EVENT_EMAIL_TEMPLATES.get(notification_type)
    if not template:
        return False
    subject = template["subject"]
    message = template["body"].format(**context) if context else template["body"]
    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[recipient_email],
    )
    return True
