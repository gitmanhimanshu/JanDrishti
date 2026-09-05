"""Audit read API. Administrators only, and read-only by design."""

from __future__ import annotations

from django_filters import rest_framework as filters
from rest_framework import serializers
from rest_framework.generics import ListAPIView

from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.permissions import IsAdmin

from ..models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "action",
            "actor_label",
            "target",
            "metadata",
            "ip_address",
            "request_id",
            "created_at",
        ]


class AuditLogFilter(filters.FilterSet):
    action = filters.CharFilter(lookup_expr="icontains")
    target = filters.CharFilter(lookup_expr="icontains")
    since = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="gte")
    until = filters.IsoDateTimeFilter(field_name="created_at", lookup_expr="lte")

    class Meta:
        model = AuditLog
        fields = ["action", "target", "since", "until"]


class AuditLogListView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AuditLogSerializer
    pagination_class = StandardPageNumberPagination
    filterset_class = AuditLogFilter
    queryset = AuditLog.objects.all()
