from rest_framework.permissions import BasePermission


class IsApplicant(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "APPLICANT"
        )


class IsReviewOfficer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "REVIEW_OFFICER"
        )


class IsInspector(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "INSPECTOR"
        )


class IsSeniorOfficer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "SENIOR_OFFICER"
        )


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "ADMIN"
        )


class IsAdminOrSeniorOfficer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("ADMIN", "SENIOR_OFFICER")
        )
