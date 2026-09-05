from django.urls import path

from .views import MediaUploadView

app_name = "media"

urlpatterns = [path("upload/", MediaUploadView.as_view(), name="upload")]
