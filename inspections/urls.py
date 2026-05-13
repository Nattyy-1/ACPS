from django.urls import path
from .views import (
    CommenceConstructionView,
    ApplicationInspectionListView,
    InspectorScheduleView,
)

urlpatterns = [
    path(
        "applications/<uuid:application_id>/commence/",
        CommenceConstructionView.as_view(),
        name="commence-construction",
    ),
    path(
        "applications/<uuid:application_id>/inspections/",
        ApplicationInspectionListView.as_view(),
        name="application-inspections",
    ),
    path(
        "inspections/my-schedule/",
        InspectorScheduleView.as_view(),
        name="inspector-schedule",
    ),
]
