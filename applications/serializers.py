from rest_framework import serializers
from .models import Application


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
