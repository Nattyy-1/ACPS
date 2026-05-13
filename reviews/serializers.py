from rest_framework import serializers
from .models import ReviewComment, SLAConfig


class ReviewCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewComment
        fields = ["document", "category", "content"]

    def validate_content(self, value):
        if not value.strip():
            raise serializers.ValidationError("Content cannot be empty.")
        return value


class ReviewCommentSerializer(serializers.ModelSerializer):
    comment_id = serializers.UUIDField(source="id")
    author_name = serializers.SerializerMethodField()
    document_name = serializers.SerializerMethodField()

    class Meta:
        model = ReviewComment
        fields = [
            "comment_id", "application", "document", "author",
            "author_name", "document_name", "category", "content",
            "resolution_status", "resolved_by", "resolved_at",
            "created_at", "updated_at",
        ]

    def get_author_name(self, obj):
        return obj.author.full_name if obj.author else "Unknown"

    def get_document_name(self, obj):
        return obj.document.file_name if obj.document else None


class ReviewDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    regulation_citation = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["decision"] == "REJECTED":
            if len(data.get("notes", "")) < 100:
                raise serializers.ValidationError(
                    "Notes must be at least 100 characters for rejection."
                )
            if not data.get("regulation_citation"):
                raise serializers.ValidationError(
                    "Regulation citation is required for rejection."
                )
        return data


class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfig
        fields = "__all__"
