import datetime
from decimal import Decimal
from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationDetailSerializer,
    ApplicationHistorySerializer,
    ApplicationListSerializer,
    ApplicationUpdateSerializer,
    ApplicationDocumentSerializer,
    ApplicationHistorySerializer,
    NeighborCreateSerializer,
    NeighborSerializer,
    RequiredDocumentSerializer,
)
from .models import Application, ApplicationHistory, Document, NeighborConsent
from accounts.permissions import (
    IsAdmin,
    IsAdminOrSeniorOfficer,
    IsApplicant,
    IsInspector,
    IsReviewOfficer,
    IsSeniorOfficer,
)
from payments.models import Payment


class ApplicationCreateView(APIView):
    authentication_classes = [JWTAuthentication]

    def get_permissions(self):
        if self.request.method == "GET":
            role = getattr(self.request.user, "role", None)
            if role == "APPLICANT":
                return [IsApplicant()]
            elif role == "REVIEW_OFFICER":
                return [IsReviewOfficer()]
            elif role == "INSPECTOR":
                return [IsInspector()]
            elif role == "SENIOR_OFFICER":
                return [IsSeniorOfficer()]
            return [IsAdmin()]
        return [IsApplicant()]

    def get(self, request):
        user = request.user
        if user.role == "APPLICANT":
            qs = Application.objects.filter(applicant=user)
        elif user.role == "REVIEW_OFFICER":
            qs = Application.objects.filter(assigned_officer=user)
        else:
            qs = Application.objects.all()

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter.upper())

        qs = qs.order_by("-created_at")
        serializer = ApplicationListSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ApplicationCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApplicationFeeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def get(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(app.get_fee_breakdown())


class ApplicationUpdateView(APIView):
    authentication_classes = [JWTAuthentication]

    ALLOWED_STATUSES = {"DRAFT", "REVISION_REQUIRED"}

    def get_permissions(self):
        if self.request.method == "GET":
            role = getattr(self.request.user, "role", None)
            if role == "APPLICANT":
                return [IsApplicant()]
            elif role == "REVIEW_OFFICER":
                return [IsReviewOfficer()]
            elif role == "INSPECTOR":
                return [IsInspector()]
            elif role == "SENIOR_OFFICER":
                return [IsSeniorOfficer()]
            return [IsAdmin()]
        return [IsApplicant()]

    def get(self, request, application_id):
        user = request.user
        try:
            if user.role == "APPLICANT":
                app = Application.objects.get(pk=application_id, applicant=user)
            elif user.role == "REVIEW_OFFICER":
                app = Application.objects.get(
                    pk=application_id, assigned_officer=user
                )
            else:
                app = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ApplicationDetailSerializer(app)
        return Response(serializer.data)

    def put(self, request, application_id):
        user = request.user
        try:
            app = Application.objects.get(pk=application_id, applicant=user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status not in self.ALLOWED_STATUSES:
            return Response(
                {
                    "detail": f"Application can only be updated when status is DRAFT or REVISION_REQUIRED. Current status: {app.status}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ApplicationUpdateSerializer(app, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ApplicationDocumentUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.DRAFT:
            return Response(
                {"detail": "Documents can only be uploaded for DRAFT applications."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ApplicationDocumentSerializer(
            data=request.data,
            context={"request": request, "application": app},
        )
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApplicationRequiredDocumentsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def get(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        required_types = app.get_required_document_types()
        uploaded = {
            d.document_type: d
            for d in Document.objects.filter(
                application=app, is_current=True
            )
        }
        checklist = []
        for dt in required_types:
            doc = uploaded.get(dt)
            checklist.append({
                "document_type": dt,
                "label": Document.DocumentType(dt).label,
                "uploaded": doc is not None,
                "accepted": doc.validation_status == Document.ValidationStatus.ACCEPTED if doc else False,
                "status": doc.validation_status if doc else None,
            })
        serializer = RequiredDocumentSerializer(checklist, many=True)
        return Response(serializer.data)


class ApplicationSubmitView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def post(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.DRAFT:
            return Response(
                {"detail": f"Only DRAFT applications can be submitted. Current status: {app.status}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        required_types = app.get_required_document_types()
        uploaded = {
            d.document_type: d
            for d in Document.objects.filter(
                application=app, is_current=True
            )
        }
        missing = []
        for dt in required_types:
            doc = uploaded.get(dt)
            if not doc:
                missing.append({
                    "document_type": dt,
                    "label": Document.DocumentType(dt).label,
                    "reason": "Not uploaded",
                })
            elif doc.validation_status == Document.ValidationStatus.REJECTED:
                missing.append({
                    "document_type": dt,
                    "label": Document.DocumentType(dt).label,
                    "reason": f"Status is {doc.validation_status}",
                })

        if missing:
            return Response(
                {
                    "detail": "Completeness check failed.",
                    "missing_documents": missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        neighbor_count = app.neighbors.count()
        if neighbor_count == 0:
            return Response(
                {
                    "detail": "At least one neighbor consent record is required before submission.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            ApplicationHistory.objects.create(
                application=app,
                previous_status=Application.Status.DRAFT,
                new_status=Application.Status.PAYMENT_PENDING,
                actor=request.user,
                note="Application submitted by applicant.",
            )
            app.status = Application.Status.PAYMENT_PENDING
            app.save(update_fields=["status"])

            year = datetime.date.today().year
            prefix = f"INV-{year}-"
            last_payment = Payment.objects.filter(
                invoice_id__startswith=prefix
            ).order_by("invoice_id").last()
            next_num = (
                int(last_payment.invoice_id.split("-")[-1]) + 1
                if last_payment else 1
            )
            invoice_id = f"{prefix}{next_num:06d}"

            Payment.objects.create(
                application=app,
                invoice_id=invoice_id,
                amount_etb=app.calculated_fee or Decimal("0"),
                status=Payment.Status.PENDING,
            )

        return Response(
            {
                "application_id": str(app.id),
                "arn": app.arn,
                "status": app.status,
                "invoice_id": invoice_id,
                "amount_etb": float(app.calculated_fee or 0),
            },
            status=status.HTTP_200_OK,
        )


class ApplicationDocumentDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def delete(self, request, application_id, document_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.DRAFT:
            return Response(
                {"detail": "Documents can only be deleted for DRAFT applications."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            doc = Document.objects.get(pk=document_id, application=app)
        except Document.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        doc.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationDocumentDownloadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, application_id, document_id):
        try:
            app = Application.objects.get(pk=application_id)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        role = getattr(request.user, "role", None)
        is_owner = request.user == app.applicant
        is_assigned = request.user == app.assigned_officer
        is_staff = role in ("SENIOR_OFFICER", "ADMIN", "INSPECTOR")

        if not (is_owner or is_assigned or is_staff):
            return Response(
                {"detail": "You do not have permission to download this document."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            doc = Document.objects.get(pk=document_id, application=app)
        except Document.DoesNotExist:
            return Response(
                {"detail": "Document not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not doc.file_path:
            return Response(
                {"detail": "No file available for this document."},
                status=status.HTTP_404_NOT_FOUND,
            )

        content_type = doc.mime_type or "application/octet-stream"
        return FileResponse(
            doc.file_path.open("rb"),
            content_type=content_type,
            filename=doc.file_name,
        )


class ApplicationNeighborView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        neighbors = app.neighbors.all()
        serializer = NeighborSerializer(neighbors, many=True)
        return Response(serializer.data)

    def post(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.DRAFT:
            return Response(
                {"detail": "Neighbors can only be added to DRAFT applications."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = NeighborCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(application=app)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ApplicationNeighborDeleteView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def delete(self, request, application_id, neighbor_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if app.status != Application.Status.DRAFT:
            return Response(
                {"detail": "Neighbors can only be deleted for DRAFT applications."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            neighbor = NeighborConsent.objects.get(pk=neighbor_id, application=app)
        except NeighborConsent.DoesNotExist:
            return Response(
                {"detail": "Neighbor not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        neighbor.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ApplicationTimelineView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

    def get(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
        except Application.DoesNotExist:
            return Response(
                {"detail": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        history = ApplicationHistory.objects.filter(application=app)
        serializer = ApplicationHistorySerializer(history, many=True)
        return Response(serializer.data)
