from django.urls import path
from .views import (
    ApplicationCreateView,
    ApplicationFeeView,
    ApplicationUpdateView,
    ApplicationDocumentUploadView,
    ApplicationRequiredDocumentsView,
)

urlpatterns = [
    path("applications/", ApplicationCreateView.as_view(), name="application-create"),
    path(
        "applications/<uuid:application_id>/fee/",
        ApplicationFeeView.as_view(),
        name="application-fee",
    ),
    path(
        "applications/<uuid:application_id>/",
        ApplicationUpdateView.as_view(),
        name="application-update",
    ),
    path(
        "applications/<uuid:application_id>/documents/",
        ApplicationDocumentUploadView.as_view(),
        name="application-document-upload",
    ),
    path(
        "applications/<uuid:application_id>/required-documents/",
        ApplicationRequiredDocumentsView.as_view(),
        name="application-required-documents",
    ),
]
