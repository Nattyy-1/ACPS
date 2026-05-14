import datetime
import io
import time
from decimal import Decimal

from django.core.mail import send_mail
from django.db import transaction
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin, IsApplicant
from applications.models import Application, ApplicationHistory, Document
from notifications.models import Notification
from .models import Payment
from .serializers import InvoiceDetailSerializer, PaymentConfirmSerializer


BANK_ACCOUNT_DETAILS = {
    "bank_name": "Commercial Bank of Ethiopia",
    "account_name": "Addis Ababa City Administration",
    "account_number": "1000001234567",
    "branch": "Head Office",
    "reference_note": "Use your ARN as payment reference.",
}


class InvoiceDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def get(self, request, invoice_id):
        try:
            payment = Payment.objects.get(
                invoice_id=invoice_id, application__applicant=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = InvoiceDetailSerializer(payment)
        return Response(serializer.data)


class InvoicePayView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def post(self, request, invoice_id):
        try:
            payment = Payment.objects.get(
                invoice_id=invoice_id, application__applicant=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if payment.status != Payment.Status.PENDING:
            return Response(
                {"detail": f"Payment already has status: {payment.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PaymentConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        method = serializer.validated_data["payment_method"]
        app = payment.application

        if method in (Payment.PaymentMethod.TELEBIRR, Payment.PaymentMethod.CBEBIRR):
            time.sleep(3)
            txn_ref = f"TXN-{datetime.date.today().year}-{payment.invoice_id.split('-')[-1]}"

            with transaction.atomic():
                payment.payment_method = method
                payment.transaction_reference = txn_ref
                payment.status = Payment.Status.CONFIRMED
                payment.paid_at = timezone.now()
                payment.save()

                ApplicationHistory.objects.create(
                    application=app,
                    previous_status=app.status,
                    new_status=Application.Status.AWAITING_ASSIGNMENT,
                    actor=request.user,
                    note=f"Payment confirmed via {method}.",
                )
                app.status = Application.Status.AWAITING_ASSIGNMENT
                app.save(update_fields=["status"])

                receipt = self._generate_receipt(payment)
                payment.receipt_path.save(
                    f"receipt_{payment.invoice_id}.pdf", receipt, save=True
                )

                Document.objects.create(
                    application=app,
                    uploader=request.user,
                    document_type="RECEIPT",
                    file_path=payment.receipt_path,
                    file_name=f"receipt_{payment.invoice_id}.pdf",
                    file_size_bytes=receipt.tell(),
                    mime_type="application/pdf",
                    validation_status=Document.ValidationStatus.ACCEPTED,
                    is_current=True,
                )

            send_mail(
                subject="Payment Receipt",
                message=(
                    f"Dear {request.user.full_name},\n\n"
                    f"Your payment of ETB {float(payment.amount_etb):.2f} "
                    f"for {app.arn} has been confirmed.\n"
                    f"Transaction: {txn_ref}\n"
                    f"Receipt: {payment.receipt_path.url if payment.receipt_path else 'N/A'}\n\n"
                    f"Thank you."
                ),
                from_email=None,
                recipient_list=[request.user.email],
            )

            Notification.objects.create(
                recipient=request.user,
                title="Payment Confirmed",
                body=f"Payment of ETB {float(payment.amount_etb):.2f} for {app.arn} confirmed.",
                notification_type="PAYMENT_CONFIRMED",
                reference_id=str(app.id),
                reference_type="APPLICATION",
            )

            return Response(
                {
                    "status": payment.status,
                    "transaction_reference": txn_ref,
                    "receipt_url": payment.receipt_path.url
                    if payment.receipt_path
                    else None,
                    "application_status": app.status,
                }
            )

        elif method == Payment.PaymentMethod.BANK_TRANSFER:
            payment.payment_method = method
            payment.status = Payment.Status.AWAITING_MANUAL_CONFIRMATION
            payment.save(update_fields=["payment_method", "status"])

            return Response(
                {
                    "status": payment.status,
                    "bank_details": BANK_ACCOUNT_DETAILS,
                    "message": (
                        "Please transfer the amount to the account below "
                        "and upload the receipt."
                    ),
                }
            )

        return Response(
            {"detail": "Invalid payment method."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _generate_receipt(self, payment):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, height - 50, "PAYMENT RECEIPT")
        c.setFont("Helvetica", 11)
        y = height - 90
        for label, val in [
            ("ARN", payment.application.arn),
            ("Invoice", payment.invoice_id),
            ("Amount (ETB)", f"{float(payment.amount_etb):.2f}"),
            ("Method", payment.get_payment_method_display()),
            ("Transaction Ref", payment.transaction_reference),
            ("Paid At", payment.paid_at.strftime("%Y-%m-%d %H:%M") if payment.paid_at else ""),
        ]:
            c.drawString(40, y, f"{label}: {val}")
            y -= 20
        c.save()
        buf.seek(0)
        return buf


class BankReceiptUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, invoice_id):
        try:
            payment = Payment.objects.get(
                invoice_id=invoice_id, application__applicant=request.user
            )
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if payment.status != Payment.Status.AWAITING_MANUAL_CONFIRMATION:
            return Response(
                {
                    "detail": f"Bank receipt can only be uploaded for "
                    f"AWAITING_MANUAL_CONFIRMATION payments. "
                    f"Current status: {payment.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        file = request.FILES.get("receipt")
        if not file:
            return Response(
                {"detail": "Receipt file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size == 0:
            return Response(
                {"detail": "File cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if file.size > 10 * 1024 * 1024:
            return Response(
                {"detail": "File size must not exceed 10MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payment.receipt_path.save(
            f"bank_receipt_{payment.invoice_id}.pdf", file, save=True
        )
        return Response(
            {
                "detail": "Receipt uploaded successfully.",
                "receipt_url": payment.receipt_path.url,
            }
        )


class InvoiceConfirmView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def put(self, request, invoice_id):
        try:
            payment = Payment.objects.get(invoice_id=invoice_id)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if payment.status != Payment.Status.AWAITING_MANUAL_CONFIRMATION:
            return Response(
                {
                    "detail": f"Cannot confirm payment with status: {payment.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        txn_ref = (
            f"TXN-{datetime.date.today().year}-"
            f"{payment.invoice_id.split('-')[-1]}"
        )

        with transaction.atomic():
            payment.transaction_reference = txn_ref
            payment.status = Payment.Status.CONFIRMED
            payment.paid_at = timezone.now()
            payment.confirmed_by = request.user
            payment.save()

            app = payment.application
            ApplicationHistory.objects.create(
                application=app,
                previous_status=app.status,
                new_status=Application.Status.AWAITING_ASSIGNMENT,
                actor=request.user,
                note="Bank transfer payment confirmed by admin.",
            )
            app.status = Application.Status.AWAITING_ASSIGNMENT
            app.save(update_fields=["status"])

        Notification.objects.create(
            recipient=payment.application.applicant,
            title="Payment Confirmed",
            body=f"Your bank transfer payment for {payment.application.arn} has been confirmed.",
            notification_type="PAYMENT_CONFIRMED",
            reference_id=str(payment.application.id),
            reference_type="APPLICATION",
        )

        head, sep, tail = payment.invoice_id.partition("-")
        send_mail(
            subject="Payment Confirmed",
            message=(
                f"Dear {payment.application.applicant.full_name},\n\n"
                f"Your bank transfer payment of ETB {float(payment.amount_etb):.2f} "
                f"for {payment.application.arn} has been confirmed by our team.\n"
                f"Transaction: {txn_ref}\n\nThank you."
            ),
            from_email=None,
            recipient_list=[payment.application.applicant.email],
        )

        return Response(
            {
                "status": payment.status,
                "transaction_reference": txn_ref,
                "application_status": app.status,
            }
        )


class ReceiptDownloadView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, receipt_id):
        try:
            payment = Payment.objects.get(pk=receipt_id)
        except Payment.DoesNotExist:
            return Response(
                {"detail": "Receipt not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not payment.receipt_path:
            return Response(
                {"detail": "No receipt file available."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(
            payment.receipt_path.open("rb"),
            content_type="application/pdf",
            filename=f"receipt_{payment.invoice_id}.pdf",
        )


class PaymentListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = Payment.objects.all().order_by("-created_at")

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        method_filter = request.query_params.get("method")
        if method_filter:
            qs = qs.filter(payment_method=method_filter.upper())

        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size
        total = qs.count()
        results = qs[start:end]

        data = []
        for p in results:
            data.append(
                {
                    "payment_id": str(p.id),
                    "invoice_id": p.invoice_id,
                    "arn": p.application.arn,
                    "applicant": p.application.applicant.full_name,
                    "amount_etb": float(p.amount_etb),
                    "method": p.payment_method,
                    "status": p.status,
                    "transaction_reference": p.transaction_reference,
                    "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                    "created_at": p.created_at.isoformat(),
                }
            )

        return Response(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "results": data,
            }
        )


class PaymentExpiryCronView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def post(self, request):
        from django.utils import timezone

        now = timezone.now()
        cutoff = now - datetime.timedelta(days=7)
        expired = Payment.objects.filter(
            status__in=[Payment.Status.PENDING, Payment.Status.AWAITING_MANUAL_CONFIRMATION],
            created_at__lt=cutoff,
        )
        count = 0
        for payment in expired:
            with transaction.atomic():
                app = payment.application
                ApplicationHistory.objects.create(
                    application=app,
                    previous_status=app.status,
                    new_status=Application.Status.PAYMENT_EXPIRED,
                    actor=None,
                    note="Payment expired after 7 days.",
                )
                app.status = Application.Status.PAYMENT_EXPIRED
                app.save(update_fields=["status"])
                payment.status = Payment.Status.EXPIRED
                payment.save(update_fields=["status"])
            count += 1

        return Response({"expired_count": count})
