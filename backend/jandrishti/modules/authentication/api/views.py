"""Authentication endpoints."""

from __future__ import annotations

from django.conf import settings
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.modules.accounts.api.serializers import MeSerializer
from jandrishti.shared.api.response import ok
from jandrishti.shared.api.throttling import AuthEndpointThrottle
from jandrishti.shared.api.views import ActorMixin

from ..application.sign_in import (
    RefreshSessionCommand,
    RefreshSessionUseCase,
    SignInWithGoogleCommand,
    SignInWithGoogleUseCase,
    SignOutCommand,
    SignOutUseCase,
)
from ..infrastructure.google import GoogleIdentityProvider
from ..models import OAuthState


class GoogleStartSerializer(serializers.Serializer):
    next = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_next(self, value: str) -> str:
        """Only same-site relative paths, so the state cannot become an open redirect."""
        if value and (not value.startswith("/") or value.startswith("//")):
            raise serializers.ValidationError("Return path must be a relative path.")
        return value


class GoogleCallbackSerializer(serializers.Serializer):
    code = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)
    state = serializers.CharField(required=False, allow_blank=True)
    redirect_uri = serializers.URLField(required=False, allow_blank=True)

    def validate(self, attrs: dict) -> dict:
        if not (attrs.get("code") or attrs.get("id_token")):
            raise serializers.ValidationError("Provide either `code` or `id_token`.")
        return attrs


class RefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class SignOutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=False, allow_blank=True)
    all_sessions = serializers.BooleanField(required=False, default=False)


def _session_payload(result) -> dict:
    return {
        "access_token": result.access_token,
        "expires_in": result.access_expires_in,
        "refresh_token": result.refresh_token,
        "token_type": "Bearer",
        "is_new_user": result.is_new_user,
        "requires_onboarding": not result.user.onboarding_completed,
        "user": MeSerializer(result.user).data,
    }


class GoogleStartView(APIView):
    """Hands the frontend a Google URL plus a single-use state.

    `next` rides along in the state so that, after the round trip, the user
    resumes the action they were blocked on (spec 5).
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    def post(self, request: Request) -> Response:
        serializer = GoogleStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        state = OAuthState.create(next_path=serializer.validated_data.get("next", ""))
        provider = GoogleIdentityProvider()
        return ok(
            {
                "authorization_url": provider.authorization_url(state.state),
                "state": state.state,
                "client_id": settings.GOOGLE_CLIENT_ID,
            }
        )


class GoogleCallbackView(ActorMixin, APIView):
    """Exchanges a Google credential for a JanDrishti session."""

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    def post(self, request: Request) -> Response:
        serializer = GoogleCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        next_path = ""
        state_value = data.get("state")
        if state_value:
            state = OAuthState.objects.filter(pk=state_value).first()
            if state is None or not state.is_usable:
                return ok(
                    {"detail": "This sign-in link has expired. Please try again."},
                    status=400,
                )
            next_path = state.next_path
            state.consume()

        use_case = SignInWithGoogleUseCase(identity_provider=GoogleIdentityProvider())
        result = use_case.execute(
            SignInWithGoogleCommand(
                code=data.get("code", ""),
                id_token=data.get("id_token", ""),
                redirect_uri=data.get("redirect_uri") or None,
                actor=self.get_actor(),
            )
        )
        return ok({**_session_payload(result), "next": next_path})


class RefreshView(ActorMixin, APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]

    def post(self, request: Request) -> Response:
        serializer = RefreshSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = RefreshSessionUseCase().execute(
            RefreshSessionCommand(
                refresh_token=serializer.validated_data["refresh_token"], actor=self.get_actor()
            )
        )
        return ok(_session_payload(result))


class SignOutView(ActorMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SignOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        SignOutUseCase().execute(
            SignOutCommand(
                refresh_token=serializer.validated_data.get("refresh_token", ""),
                all_sessions=serializer.validated_data.get("all_sessions", False),
                actor=self.get_actor(),
            )
        )
        return ok({"signed_out": True})
