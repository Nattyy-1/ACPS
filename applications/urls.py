from django.urls import path
from .views import ApplicationCreateView

urlpatterns = [
    path("applications/", ApplicationCreateView.as_view(), name="application-create"),
]
