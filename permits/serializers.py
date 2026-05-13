from rest_framework import serializers
from .models import Permit


class PublicPermitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permit
        fields = [
            "permit_number", "status", "issue_date", "expiry_date",
        ]


class AuthenticatedPermitSerializer(serializers.ModelSerializer):
    permit_id = serializers.UUIDField(source="id")
    application_id = serializers.UUIDField(source="application.id")
    arn = serializers.CharField(source="application.arn", read_only=True)
    plot_address = serializers.CharField(source="application.plot_address", read_only=True)
    subcity_id = serializers.CharField(source="application.subcity_id", read_only=True)
    building_category = serializers.CharField(source="application.building_category", read_only=True)

    class Meta:
        model = Permit
        fields = [
            "permit_id", "permit_number", "permit_type",
            "application_id", "arn", "issued_by",
            "issue_date", "expiry_date", "status",
            "plot_address", "subcity_id", "building_category",
            "document_path", "created_at",
        ]
