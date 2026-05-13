from rest_framework import serializers
from .models import Application, Document


class ApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "intended_use",
            "height_m",
            "floors_above",
            "floors_below",
            "floor_area_sqm",
            "plot_address",
            "plot_gps_lat",
            "plot_gps_lng",
            "subcity_id",
            "woreda",
            "architect_name",
            "architect_license",
            "contractor_name",
            "contractor_license",
            "project_value_etb",
        )

    def create(self, validated_data):
        user = self.context["request"].user
        project_value = validated_data.get("project_value_etb")
        calculated_fee = (
            Application.calculate_fee(project_value) if project_value else None
        )
        arn = Application.generate_arn()
        validated_data.pop("building_category", None)
        app = Application(
            **validated_data, applicant=user, arn=arn, calculated_fee=calculated_fee
        )
        app.save()
        return app

    def to_representation(self, instance):
        return {
            "application_id": str(instance.id),
            "arn": instance.arn,
            "status": instance.status,
            "building_category": instance.building_category,
            "calculated_fee": float(instance.calculated_fee)
            if instance.calculated_fee
            else None,
        }


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "intended_use",
            "height_m",
            "floors_above",
            "floors_below",
            "floor_area_sqm",
            "plot_address",
            "plot_gps_lat",
            "plot_gps_lng",
            "subcity_id",
            "woreda",
            "architect_name",
            "architect_license",
            "contractor_name",
            "contractor_license",
            "project_value_etb",
        )
        extra_kwargs = {f: {"required": False} for f in fields}

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.building_category = instance.auto_classify()
        if instance.project_value_etb:
            instance.calculated_fee = Application.calculate_fee(
                instance.project_value_etb
            )
        instance.save()
        return instance

    def to_representation(self, instance):
        return {
            "application_id": str(instance.id),
            "arn": instance.arn,
            "status": instance.status,
            "building_category": instance.building_category,
            "calculated_fee": float(instance.calculated_fee)
            if instance.calculated_fee
            else None,
        }


class ApplicationDocumentSerializer(serializers.Serializer):
    document_type = serializers.ChoiceField(
        choices=[
            "ARCHITECTURAL",
            "STRUCTURAL",
            "SANITARY",
            "ELECTRICAL",
            "SOIL_TEST",
            "PROFESSIONAL_LICENSE",
            "FIRE_SAFETY",
        ]
    )
    file = serializers.FileField()

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/acad",
        "application/x-autocad",
        "image/vnd.dwg",
        "application/dwg",
    }

    def validate_file(self, value):
        if value.size == 0:
            raise serializers.ValidationError("File cannot be empty.")
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError("File size must not exceed 20MB.")
        if value.content_type not in self.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError("File must be PDF or DWG.")
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        user = self.context["request"].user
        application = self.context["application"]

        Document.objects.filter(
            application=application,
            document_type=validated_data["document_type"],
            is_current=True,
        ).update(is_current=False)

        latest = (
            Document.objects.filter(
                application=application,
                document_type=validated_data["document_type"],
            )
            .order_by("-version_number")
            .first()
        )
        next_version = (latest.version_number + 1) if latest else 1

        doc = Document.objects.create(
            application=application,
            uploader=user,
            document_type=validated_data["document_type"],
            file_path=file,
            file_name=file.name,
            file_size_bytes=file.size,
            mime_type=file.content_type,
            version_number=next_version,
            is_current=True,
        )
        return doc

    def to_representation(self, instance):
        return {
            "document_id": str(instance.id),
            "document_type": instance.document_type,
            "file_name": instance.file_name,
            "file_size_bytes": instance.file_size_bytes,
            "mime_type": instance.mime_type,
            "version_number": instance.version_number,
            "status": instance.validation_status,
        }
