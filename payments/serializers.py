from rest_framework import serializers
from .models import Payment


class InvoiceDetailSerializer(serializers.ModelSerializer):
    invoice_id = serializers.CharField()
    amount_etb = serializers.SerializerMethodField()
    available_methods = serializers.SerializerMethodField()
    application_arn = serializers.SerializerMethodField()
    application_id = serializers.SerializerMethodField()
    fee_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            "invoice_id", "amount_etb", "status", "payment_method",
            "available_methods", "application_arn", "application_id",
            "fee_breakdown", "created_at",
        ]

    def get_amount_etb(self, obj):
        return float(obj.amount_etb)

    def get_available_methods(self, obj):
        return [m[0] for m in Payment.PaymentMethod.choices]

    def get_application_arn(self, obj):
        return obj.application.arn

    def get_application_id(self, obj):
        return str(obj.application.id)

    def get_fee_breakdown(self, obj):
        return obj.application.get_fee_breakdown()


class PaymentConfirmSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=Payment.PaymentMethod.choices
    )
