from django.urls import path

from .views import BookmarkListView, BookmarkToggleView, FollowListView, FollowToggleView

app_name = "social"

urlpatterns = [
    path("bookmarks/", BookmarkListView.as_view(), name="bookmarks"),
    path("bookmarks/toggle/", BookmarkToggleView.as_view(), name="bookmark-toggle"),
    path("follows/", FollowListView.as_view(), name="follows"),
    path("follows/toggle/", FollowToggleView.as_view(), name="follow-toggle"),
]
