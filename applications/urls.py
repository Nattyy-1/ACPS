from django.urls import path
from .views import ApplicationCreateView, ApplicationFeeView, ApplicationUpdateView

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
]
