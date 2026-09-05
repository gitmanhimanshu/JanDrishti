from django.urls import path

from .views import ClusterDetachView, ClusterDetailView, ClusterListView, ClusterMergeView

app_name = "issue_clustering"

urlpatterns = [
    path("", ClusterListView.as_view(), name="list"),
    path("<uuid:cluster_id>/", ClusterDetailView.as_view(), name="detail"),
    path("<uuid:cluster_id>/merge/", ClusterMergeView.as_view(), name="merge"),
    path("<uuid:cluster_id>/detach/", ClusterDetachView.as_view(), name="detach"),
]
