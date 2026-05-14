from django.urls import path
from .views import (
    AdminStatsView,
    AuditLogView,
    FeeScheduleConfigView,
    SLAConfigView,
    InspectionChecklistConfigView,
    NotificationTemplateConfigView,
    ReportsExportView,
    SignatureView,
)

urlpatterns = [
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("admin/audit-log/", AuditLogView.as_view(), name="admin-audit-log"),
    path(
        "admin/config/fee-schedule/",
        FeeScheduleConfigView.as_view(),
        name="admin-fee-schedule",
    ),
    path(
        "admin/config/sla-thresholds/",
        SLAConfigView.as_view(),
        name="admin-sla-thresholds",
    ),
    path(
        "admin/config/inspection-checklists/<str:inspection_type>/",
        InspectionChecklistConfigView.as_view(),
        name="admin-inspection-checklists",
    ),
    path(
        "admin/config/notification-templates/",
        NotificationTemplateConfigView.as_view(),
        name="admin-notification-templates",
    ),
    path(
        "admin/reports/export/",
        ReportsExportView.as_view(),
        name="admin-reports-export",
    ),
    path(
        "admin/signatures/<uuid:user_id>/",
        SignatureView.as_view(),
        name="admin-signature",
    ),
]
