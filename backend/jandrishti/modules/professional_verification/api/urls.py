from django.urls import path

from .views import (
    DocumentAccessView,
    MyVerificationView,
    PrivateDocumentUploadView,
    ReviewQueueView,
    ReviewVerificationView,
    SubmitVerificationView,
)

app_name = "professional_verification"

urlpatterns = [
    path("me/", MyVerificationView.as_view(), name="mine"),
    path("submit/", SubmitVerificationView.as_view(), name="submit"),
    path("documents/upload/", PrivateDocumentUploadView.as_view(), name="document-upload"),
    path(
        "documents/<uuid:document_id>/access/", DocumentAccessView.as_view(), name="document-access"
    ),
    path("queue/", ReviewQueueView.as_view(), name="queue"),
    path("<uuid:verification_id>/review/", ReviewVerificationView.as_view(), name="review"),
]
