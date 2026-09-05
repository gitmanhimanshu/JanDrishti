from django.urls import path

from .views import CategoryTreeView, DepartmentListView, StateListView

app_name = "catalog"

urlpatterns = [
    path("categories/", CategoryTreeView.as_view(), name="categories"),
    path("departments/", DepartmentListView.as_view(), name="departments"),
    path("states/", StateListView.as_view(), name="states"),
]
