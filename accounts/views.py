from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView, TokenBlacklistView
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    UserProfileSerializer,
    AdminUserSerializer,
    CreateOfficerSerializer,
    VaultDocumentSerializer,
)
from .permissions import IsAdmin, IsApplicant

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Account created", "user_id": str(user.id)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        from .models import LoginAttemptLog

        email = request.data.get("email", "")
        ip = request.META.get("REMOTE_ADDR", "")
        try:
            response = super().post(request, *args, **kwargs)
        except Exception:
            LoginAttemptLog.objects.create(email=email, ip_address=ip, success=False)
            raise
        LoginAttemptLog.objects.create(email=email, ip_address=ip, success=True)
        return response


class LogoutView(TokenBlacklistView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
            token = PasswordResetTokenGenerator().make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"http://localhost:3000/reset-password/{uid}/{token}/"
            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_url}",
                from_email=None,
                recipient_list=[email],
            )
        except User.DoesNotExist:
            pass

        return Response(
            {"message": "Password reset link sent to your email"},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password has been reset successfully"},
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserProfileSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminUserDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = AdminUserSerializer(user)
        return Response(serializer.data)


class AdminUserListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def get(self, request):
        queryset = User.objects.all().order_by("id")
        role = request.query_params.get("role")
        status_param = request.query_params.get("status")
        if role:
            queryset = queryset.filter(role=role)
        if status_param:
            queryset = queryset.filter(status=status_param)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AdminUserSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = AdminUserSerializer(queryset, many=True)
        return Response(serializer.data)

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            from rest_framework.pagination import PageNumberPagination

            self._paginator = PageNumberPagination()
            self._paginator.page_size = 20
            self._paginator.page_query_param = "page"
        return self._paginator

    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)

    def post(self, request):
        serializer = CreateOfficerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminDeactivateUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdmin]

    def put(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND
            )
        user.status = "INACTIVE"
        user.is_active = False
        user.save(update_fields=["status", "is_active"])
        return Response(
            {"message": "User account deactivated", "user_id": str(user.id)},
            status=status.HTTP_200_OK,
        )


class VaultDocumentUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def post(self, request):
        serializer = VaultDocumentSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
