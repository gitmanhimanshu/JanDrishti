"""
Categories and departments (spec 37, 38).

Both are hierarchies, both are administrator-managed rather than hardcoded, and
both use a materialised `path` so that "everything under Infrastructure" is one
indexed prefix query instead of a recursive walk.
"""

from __future__ import annotations

from django.db import models
from django.utils.text import slugify

from jandrishti.shared.models import BaseEntity


class TreeQuerySet(models.QuerySet):
    def roots(self) -> TreeQuerySet:
        return self.filter(parent__isnull=True)

    def active(self) -> TreeQuerySet:
        return self.filter(is_active=True)

    def descendants_of(self, node: TreeNode) -> TreeQuerySet:
        return self.filter(path__startswith=f"{node.path}/")

    def subtree_of(self, node: TreeNode) -> TreeQuerySet:
        return self.filter(models.Q(pk=node.pk) | models.Q(path__startswith=f"{node.path}/"))


class TreeNode(BaseEntity):
    """Shared hierarchy behaviour for Category and Department."""

    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=180, db_index=True)
    description = models.TextField(max_length=1000, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Slash-joined slugs from the root, e.g. "infrastructure/roads".
    path = models.CharField(max_length=600, db_index=True, editable=False)
    depth = models.PositiveSmallIntegerField(default=0, editable=False)
    display_order = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True, db_index=True)

    objects = TreeQuerySet.as_manager()

    class Meta:
        abstract = True
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.path or self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:180]
        parent_path = self.parent.path if self.parent else ""
        self.path = f"{parent_path}/{self.slug}" if parent_path else self.slug
        self.depth = self.parent.depth + 1 if self.parent else 0
        super().save(*args, **kwargs)
        # A renamed parent must not leave stale child paths behind.
        for child in self.children.all():
            child.save()

    @property
    def ancestors_slugs(self) -> list[str]:
        return self.path.split("/")[:-1]


class Category(TreeNode):
    """What kind of problem this is. Drives routing and discovery."""

    icon = models.CharField(max_length=60, blank=True)
    # Free-form hints used by the AI classifier and the keyword fallback.
    keywords = models.JSONField(default=list, blank=True)

    class Meta(TreeNode.Meta):
        db_table = "catalog_category"
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(fields=["parent", "slug"], name="uq_category_parent_slug"),
        ]
        indexes = [models.Index(fields=["path"]), models.Index(fields=["is_active", "depth"])]


class Department(TreeNode):
    """Who is responsible. Hierarchical: a corporation contains its wings."""

    class Level(models.TextChoices):
        CENTRAL = "CENTRAL", "Central"
        STATE = "STATE", "State"
        DISTRICT = "DISTRICT", "District"
        MUNICIPAL = "MUNICIPAL", "Municipal"
        WARD = "WARD", "Ward"

    level = models.CharField(max_length=20, choices=Level.choices, default=Level.MUNICIPAL)
    state = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    # Public accountability figures, recomputed by the analytics module.
    avg_resolution_days = models.FloatField(null=True, blank=True)
    resolved_count = models.PositiveIntegerField(default=0)

    class Meta(TreeNode.Meta):
        db_table = "catalog_department"
        constraints = [
            models.UniqueConstraint(fields=["parent", "slug"], name="uq_department_parent_slug"),
        ]
        indexes = [
            models.Index(fields=["path"]),
            models.Index(fields=["state", "district", "city"]),
            models.Index(fields=["level", "is_active"]),
        ]


class RoutingRule(BaseEntity):
    """Category plus jurisdiction to responsible department.

    Routing is data, not code: an `if category == "roads"` chain buried in a
    view would need a deploy every time a municipality reorganises (spec 37).
    More specific rules win, which is what `specificity` orders.
    """

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="routing_rules")
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="routing_rules"
    )
    state = models.CharField(max_length=120, blank=True, db_index=True)
    district = models.CharField(max_length=120, blank=True, db_index=True)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    # Computed on save: number of jurisdiction fields the rule constrains.
    specificity = models.PositiveSmallIntegerField(default=0, editable=False, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "catalog_routing_rule"
        ordering = ["-specificity"]
        indexes = [models.Index(fields=["category", "state", "district", "city"])]

    def save(self, *args, **kwargs):
        self.specificity = sum(1 for field in (self.state, self.district, self.city) if field)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        scope = " / ".join(p for p in (self.state, self.district, self.city) if p) or "anywhere"
        return f"{self.category.name} in {scope} -> {self.department.name}"
