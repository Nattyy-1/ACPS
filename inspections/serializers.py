from rest_framework import serializers
from .models import (
    Inspection, InspectionChecklistItem, InspectionChecklistTemplate, InspectionPhoto
)


class InspectionChecklistItemSerializer(serializers.ModelSerializer):
    item_id = serializers.UUIDField(source="id")

    class Meta:
        model = InspectionChecklistItem
        fields = ["item_id", "item_text", "result", "notes", "item_template"]


class InspectionPhotoSerializer(serializers.ModelSerializer):
    photo_id = serializers.UUIDField(source="id")

    class Meta:
        model = InspectionPhoto
        fields = ["photo_id", "file", "taken_at"]


class InspectionSerializer(serializers.ModelSerializer):
    inspection_id = serializers.UUIDField(source="id")
    assigned_inspector_name = serializers.SerializerMethodField()
    checklist_items = InspectionChecklistItemSerializer(many=True, read_only=True)
    photos = InspectionPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Inspection
        fields = [
            "inspection_id", "inspection_type", "scheduled_date",
            "assigned_inspector", "assigned_inspector_name",
            "status", "start_timestamp", "overall_result",
            "failure_summary", "submitted_at", "checklist_items", "photos",
            "created_at", "updated_at",
        ]

    def get_assigned_inspector_name(self, obj):
        return obj.assigned_inspector.full_name if obj.assigned_inspector else None


class InspectionChecklistUpdateSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.DictField(), allow_empty=False)

    def validate_items(self, value):
        for item in value:
            if "item_id" not in item:
                raise serializers.ValidationError("Each item must have an item_id.")
            result = item.get("result", "")
            if result and result not in ("PASS", "FAIL", "NA", ""):
                raise serializers.ValidationError(f"Invalid result '{result}' for item {item['item_id']}.")
        return value
