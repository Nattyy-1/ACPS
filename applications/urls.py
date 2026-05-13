from django.urls import path
from .views import ApplicationCreateView, ApplicationFeeView

urlpatterns = [
    path("applications/", ApplicationCreateView.as_view(), name="application-create"),
    path(
        "applications/<uuid:application_id>/fee/",
        ApplicationFeeView.as_view(),
        name="application-fee",
    ),
]
