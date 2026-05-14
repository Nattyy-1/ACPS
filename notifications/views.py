from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from .models import Notification


class NotificationListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user)
        unread_only = request.query_params.get("unread_only", "").lower()
        if unread_only in ("true", "1"):
            qs = qs.filter(is_read=False)
        qs = qs[:50]

        results = []
        for n in qs:
            results.append({
                "notification_id": str(n.id),
                "title": n.title,
                "body": n.body,
                "notification_type": n.notification_type,
                "reference_id": n.reference_id,
                "reference_type": n.reference_type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            })

        return Response({
            "count": len(results),
            "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
            "results": results,
        })


class NotificationReadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request, notification_id):
        try:
            n = Notification.objects.get(pk=notification_id, recipient=request.user)
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        n.is_read = True
        n.save(update_fields=["is_read"])
        return Response({"status": "read"})


class NotificationReadAllView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def put(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"marked_read": count})
