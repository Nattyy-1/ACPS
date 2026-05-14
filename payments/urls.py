from django.urls import path
from .views import (
    InvoiceDetailView,
    InvoicePayView,
    BankReceiptUploadView,
    InvoiceConfirmView,
    ReceiptDownloadView,
    PaymentListView,
    PaymentExpiryCronView,
)

urlpatterns = [
    path(
        "payments/invoices/<str:invoice_id>/",
        InvoiceDetailView.as_view(),
        name="invoice-detail",
    ),
    path(
        "payments/invoices/<str:invoice_id>/pay/",
        InvoicePayView.as_view(),
        name="invoice-pay",
    ),
    path(
        "payments/invoices/<str:invoice_id>/bank-receipt/",
        BankReceiptUploadView.as_view(),
        name="invoice-bank-receipt",
    ),
    path(
        "payments/invoices/<str:invoice_id>/confirm/",
        InvoiceConfirmView.as_view(),
        name="invoice-confirm",
    ),
    path(
        "payments/receipts/<uuid:receipt_id>/",
        ReceiptDownloadView.as_view(),
        name="receipt-download",
    ),
    path(
        "payments/",
        PaymentListView.as_view(),
        name="payment-list",
    ),
    path(
        "payments/expire/",
        PaymentExpiryCronView.as_view(),
        name="payment-expire",
    ),
]
