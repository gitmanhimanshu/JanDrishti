from django.urls import path

from .views import ModerationQueueView, ReportContentView, ResolveReportView

app_name = "moderation"

urlpatterns = [
    path("report/", ReportContentView.as_view(), name="report"),
    path("queue/", ModerationQueueView.as_view(), name="queue"),
    path("<uuid:report_id>/resolve/", ResolveReportView.as_view(), name="resolve"),
]
