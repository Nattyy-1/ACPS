from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import (
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
    ApplicationDocumentSerializer,
    RequiredDocumentSerializer,
)
from .models import Application, Document
from accounts.permissions import IsApplicant


class ApplicationCreateView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsApplicant]

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
    permission_classes = [IsApplicant]

    ALLOWED_STATUSES = {"DRAFT", "REVISION_REQUIRED"}

    def put(self, request, application_id):
        try:
            app = Application.objects.get(pk=application_id, applicant=request.user)
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
