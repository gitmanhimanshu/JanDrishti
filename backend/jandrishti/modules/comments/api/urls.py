from django.urls import path

from .views import CommentCreateView, CommentDetailView, CommentModerateView, CommentThreadView

app_name = "comments"

urlpatterns = [
    path("", CommentCreateView.as_view(), name="create"),
    path("<str:target_type>/<uuid:target_id>/", CommentThreadView.as_view(), name="thread"),
    path("<uuid:comment_id>/delete/", CommentDetailView.as_view(), name="delete"),
    path("<uuid:comment_id>/moderate/", CommentModerateView.as_view(), name="moderate"),
]
