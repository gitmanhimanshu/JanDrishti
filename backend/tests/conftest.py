"""Shared fixtures."""

from __future__ import annotations

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from jandrishti.modules.accounts.domain.enums import UserRole
from jandrishti.modules.accounts.models import User
from jandrishti.modules.authentication.infrastructure.tokens import JWTTokenService
from jandrishti.modules.catalog.models import Category, Department, RoutingRule
from jandrishti.modules.government.models import DepartmentMembership
from jandrishti.modules.problems.models import Problem


@pytest.fixture
def api() -> APIClient:
    return APIClient()


def _auth(client: APIClient, user: User) -> APIClient:
    token, _ = JWTTokenService().issue_access_token(str(user.id), user.role)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.fixture
def make_user(db):
    def factory(role: str = UserRole.CITIZEN, **kwargs) -> User:
        index = User.objects.count() + 1
        return User.objects.create_user(
            email=kwargs.pop("email", f"user{index}@example.com"),
            full_name=kwargs.pop("full_name", f"User {index}"),
            role=role,
            **kwargs,
        )

    return factory


@pytest.fixture
def citizen(make_user) -> User:
    return make_user()


@pytest.fixture
def other_citizen(make_user) -> User:
    return make_user()


@pytest.fixture
def moderator(make_user) -> User:
    return make_user(role=UserRole.MODERATOR)


@pytest.fixture
def official(make_user, department) -> User:
    user = make_user(role=UserRole.GOVERNMENT_OFFICIAL)
    DepartmentMembership.objects.create(user=user, department=department, granted_at=timezone.now())
    return user


@pytest.fixture
def auth_client(api, citizen) -> APIClient:
    return _auth(api, citizen)


@pytest.fixture
def as_user():
    def factory(user: User) -> APIClient:
        return _auth(APIClient(), user)

    return factory


@pytest.fixture
def category(db) -> Category:
    parent = Category.objects.create(name="Infrastructure")
    return Category.objects.create(name="Roads", parent=parent)


@pytest.fixture
def department(db) -> Department:
    parent = Department.objects.create(name="Municipal Corporation", level="MUNICIPAL")
    return Department.objects.create(name="Road Department", parent=parent, level="MUNICIPAL")


@pytest.fixture
def routing_rule(category, department) -> RoutingRule:
    return RoutingRule.objects.create(category=category, department=department)


@pytest.fixture
def problem(db, citizen, category, department) -> Problem:
    return Problem.objects.create(
        title="Large pothole on the main road near the school",
        description=(
            "A deep pothole has formed near the school gate and is causing accidents "
            "every morning during the school run."
        ),
        reporter=citizen,
        category=category,
        department=department,
        state="Maharashtra",
        district="Pune",
        city="Pune",
        latitude=18.5204,
        longitude=73.8567,
    )
