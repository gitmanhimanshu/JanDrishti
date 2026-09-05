from django.urls import path

from .views import GoogleCallbackView, GoogleStartView, RefreshView, SignOutView

app_name = "authentication"

urlpatterns = [
    path("google/start/", GoogleStartView.as_view(), name="google-start"),
    path("google/callback/", GoogleCallbackView.as_view(), name="google-callback"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("signout/", SignOutView.as_view(), name="signout"),
]
