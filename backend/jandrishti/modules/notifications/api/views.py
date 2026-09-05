"""Notification endpoints. Always scoped to the signed-in user."""

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.response import ok

from ..models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link_path", "metadata", "is_read", "created_at"]

    def get_is_read(self, obj: Notification) -> bool:
        return obj.read_at is not None


class NotificationListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        # Filtering by the authenticated user rather than by a client-supplied
        # id is what keeps one account from reading another account's alerts.
        queryset = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get("unread") == "true":
            queryset = queryset.filter(read_at__isnull=True)
        return queryset


class UnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
        return ok({"unread": count})


class MarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        ids = request.data.get("ids") or []
        queryset = Notification.objects.filter(recipient=request.user, read_at__isnull=True)
        if ids:
            queryset = queryset.filter(public_id__in=ids[:200])
        updated = queryset.update(read_at=timezone.now())
        return ok({"marked_read": updated})
