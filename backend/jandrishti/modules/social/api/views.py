"""Bookmark and follow endpoints. All of these require an account."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from jandrishti.shared.api.pagination import StandardPageNumberPagination
from jandrishti.shared.api.response import created, error, ok
from jandrishti.shared.api.views import ActorMixin

from ..models import Bookmark, Follow, TargetType


def resolve_target(target_type: str, public_id: str) -> Any:
    """One translation point from a public UUID to the row being followed."""
    if target_type == TargetType.PROBLEM:
        from jandrishti.modules.problems.models import Problem

        return Problem.objects.public().filter(public_id=public_id).first()
    if target_type == TargetType.EXPERIENCE:
        from jandrishti.modules.experience.models import Experience

        return Experience.objects.public().filter(public_id=public_id).first()
    if target_type == TargetType.PROJECT:
        from jandrishti.modules.projects.models import Project

        return Project.objects.filter(public_id=public_id).first()
    if target_type == TargetType.USER:
        from jandrishti.modules.accounts.models import User

        return User.objects.filter(pk=public_id, is_active=True).first()
    if target_type == TargetType.CLUSTER:
        from jandrishti.modules.issue_clustering.models import IssueCluster

        return IssueCluster.objects.filter(public_id=public_id).first()
    if target_type == TargetType.DEPARTMENT:
        from jandrishti.modules.catalog.models import Department

        return Department.objects.filter(public_id=public_id).first()
    return None


def target_title(target: Any) -> str:
    for attribute in ("title", "display_name", "name"):
        value = getattr(target, attribute, None)
        if value:
            return str(value)[:250]
    return ""


class ToggleSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=TargetType.choices)
    target_id = serializers.CharField(max_length=64)


class BookmarkSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Bookmark
        fields = ["id", "target_type", "target_public_id", "target_title", "created_at"]


class FollowSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="public_id", read_only=True)

    class Meta:
        model = Follow
        fields = [
            "id",
            "target_type",
            "target_public_id",
            "target_title",
            "notifications_enabled",
            "created_at",
        ]


class _ToggleView(ActorMixin, APIView):
    """Shared toggle behaviour. POST adds, DELETE removes; both are idempotent."""

    permission_classes = [IsAuthenticated]
    model: Any = None

    def post(self, request: Request) -> Response:
        serializer = ToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target = resolve_target(data["target_type"], data["target_id"])
        if target is None:
            return error("NOT_FOUND", "That content was not found.", status=404)

        obj, was_created = self.model.objects.get_or_create(
            user=request.user,
            target_type=data["target_type"],
            target_id=target.id,
            defaults={
                "target_public_id": getattr(target, "public_id", None) or target.pk,
                "target_title": target_title(target),
            },
        )
        return created({"active": True, "created": was_created, "id": str(obj.public_id)})

    def delete(self, request: Request) -> Response:
        serializer = ToggleSerializer(data=request.data or request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target = resolve_target(data["target_type"], data["target_id"])
        if target is None:
            return error("NOT_FOUND", "That content was not found.", status=404)

        self.model.objects.filter(
            user=request.user, target_type=data["target_type"], target_id=target.id
        ).delete()
        return ok({"active": False})


class BookmarkToggleView(_ToggleView):
    model = Bookmark


class FollowToggleView(_ToggleView):
    model = Follow


class BookmarkListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookmarkSerializer
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = Bookmark.objects.filter(user=self.request.user)
        target_type = self.request.query_params.get("target_type")
        return queryset.filter(target_type=target_type) if target_type else queryset


class FollowListView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowSerializer
    pagination_class = StandardPageNumberPagination

    def get_queryset(self):
        queryset = Follow.objects.filter(user=self.request.user)
        target_type = self.request.query_params.get("target_type")
        return queryset.filter(target_type=target_type) if target_type else queryset
