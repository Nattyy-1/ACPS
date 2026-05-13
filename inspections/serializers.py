from rest_framework import serializers
from .models import Inspection


class InspectionSerializer(serializers.ModelSerializer):
    inspection_id = serializers.UUIDField(source="id")
    assigned_inspector_name = serializers.SerializerMethodField()

    class Meta:
        model = Inspection
        fields = [
            "inspection_id", "inspection_type", "scheduled_date",
            "assigned_inspector", "assigned_inspector_name",
            "status", "start_timestamp", "overall_result",
            "failure_summary", "submitted_at", "created_at",
        ]

    def get_assigned_inspector_name(self, obj):
        return obj.assigned_inspector.full_name if obj.assigned_inspector else None
