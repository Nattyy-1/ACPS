from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from applications.models import Document

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("email", "full_name", "phone", "password")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["user_id"] = str(self.user.id)
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_uid(self, value):
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            uid = force_str(urlsafe_base64_decode(value))
            user = User.objects.get(pk=uid)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid user identifier.")
        self._reset_user = user
        return value

    def validate(self, attrs):
        token = attrs.get("token")
        user = getattr(self, "_reset_user", None)
        if user and not PasswordResetTokenGenerator().check_token(user, token):
            raise serializers.ValidationError({"token": "Invalid or expired token."})
        return attrs

    def save(self):
        user = self._reset_user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "status",
            "subcity_id",
            "land_certificate_number",
            "tin",
        )
        read_only_fields = ("id", "email", "role", "status")


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "status",
            "subcity_id",
            "land_certificate_number",
            "tin",
            "is_active",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class CreateOfficerSerializer(serializers.ModelSerializer):
    password = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("email", "full_name", "phone", "role", "subcity_id", "password")

    def validate_role(self, value):
        if value == User.Role.APPLICANT:
            raise serializers.ValidationError(
                "Officer accounts cannot have APPLICANT role."
            )
        valid_roles = [
            User.Role.REVIEW_OFFICER,
            User.Role.INSPECTOR,
            User.Role.SENIOR_OFFICER,
            User.Role.ADMIN,
        ]
        if value not in valid_roles:
            raise serializers.ValidationError(f"Invalid officer role: {value}")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def create(self, validated_data):
        import secrets
        import string

        temp_password = "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(12)
        )
        user = User.objects.create_user(
            email=validated_data["email"],
            full_name=validated_data["full_name"],
            phone=validated_data["phone"],
            password=temp_password,
            role=validated_data["role"],
            subcity_id=validated_data.get("subcity_id", ""),
        )
        self._temp_password = temp_password
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["password"] = getattr(self, "_temp_password", "")
        return data


class VaultDocumentSerializer(serializers.Serializer):
    file = serializers.FileField()
    document_type = serializers.ChoiceField(choices=["NATIONAL_ID", "TIN_CERTIFICATE"])

    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "application/pdf",
    }

    def validate_file(self, value):
        if value.size == 0:
            raise serializers.ValidationError("File cannot be empty.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size must not exceed 5MB.")
        if value.content_type not in self.ALLOWED_MIME_TYPES:
            raise serializers.ValidationError("File must be JPEG, PNG, or PDF.")
        return value

    def create(self, validated_data):
        file = validated_data["file"]
        user = self.context["request"].user
        doc = Document.objects.create(
            application=None,
            uploader=user,
            document_type=validated_data["document_type"],
            file_path=file,
            file_name=file.name,
            file_size_bytes=file.size,
            mime_type=file.content_type,
        )
        return doc

    def to_representation(self, instance):
        return {
            "document_id": str(instance.id),
            "status": instance.validation_status,
            "validation_result": "valid",
        }
