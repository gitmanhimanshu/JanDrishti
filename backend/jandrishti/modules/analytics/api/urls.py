from django.urls import path

from .views import DepartmentPerformanceView, PublicStatsView

app_name = "analytics"

urlpatterns = [
    path("public/", PublicStatsView.as_view(), name="public"),
    path("departments/", DepartmentPerformanceView.as_view(), name="departments"),
]
