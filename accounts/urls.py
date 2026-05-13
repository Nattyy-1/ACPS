from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
    CurrentUserView,
    VaultDocumentUploadView,
    AdminUserDetailView,
    AdminUserListView,
    AdminDeactivateUserView,
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path(
        "auth/forgot-password/",
        ForgotPasswordView.as_view(),
        name="auth-forgot-password",
    ),
    path(
        "auth/reset-password/", ResetPasswordView.as_view(), name="auth-reset-password"
    ),
    path(
        "users/me/documents/",
        VaultDocumentUploadView.as_view(),
        name="vault-document-upload",
    ),
    path("users/me/", CurrentUserView.as_view(), name="users-me"),
    path("users/", AdminUserListView.as_view(), name="admin-user-list"),
    path(
        "users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-user-detail"
    ),
    path(
        "users/<int:user_id>/deactivate/",
        AdminDeactivateUserView.as_view(),
        name="admin-deactivate-user",
    ),
]
