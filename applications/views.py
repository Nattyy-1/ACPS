from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import ApplicationCreateSerializer
from .models import Application
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
