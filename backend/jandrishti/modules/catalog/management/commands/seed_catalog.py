"""
Seeds the category tree, a sample department hierarchy and routing rules.

Reference data only -- no fabricated problems, supports or statistics. The
landing page shows honest zeros on a fresh install (spec 12).

    python manage.py seed_catalog
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from jandrishti.modules.catalog.models import Category, Department, RoutingRule

CATEGORY_TREE: dict[str, list[str]] = {
    "Infrastructure": ["Roads", "Bridges", "Streetlights", "Footpaths", "Public buildings"],
    "Water & Sanitation": ["Water supply", "Drainage", "Sewage", "Public toilets"],
    "Waste Management": ["Garbage collection", "Landfill", "Recycling"],
    "Healthcare": ["Hospitals", "Primary health centres", "Ambulance services", "Medicine supply"],
    "Education": ["Schools", "Colleges", "Mid-day meals", "School infrastructure"],
    "Electricity": ["Power supply", "Street power", "Billing"],
    "Transport": ["Public buses", "Traffic management", "Parking", "Railway crossings"],
    "Environment": ["Air quality", "Water pollution", "Tree cover", "Noise pollution"],
    "Public Safety": ["Street safety", "Fire safety", "Stray animals", "Flooding"],
    "Governance": ["Service delays", "Documentation", "Public grievance", "Transparency"],
}

DEPARTMENTS = [
    (
        "Municipal Corporation",
        "MUNICIPAL",
        ["Road Department", "Water Department", "Sanitation Department", "Streetlight Department"],
    ),
    ("Public Works Department", "STATE", ["Highways Wing", "Buildings Wing"]),
    ("Health Department", "STATE", ["Hospital Administration", "Public Health"]),
    ("Education Department", "STATE", ["School Education", "Higher Education"]),
    ("Electricity Board", "STATE", ["Distribution", "Billing"]),
    ("Pollution Control Board", "STATE", []),
    ("Transport Department", "STATE", ["Traffic Police", "Public Transport"]),
]

# category path -> department path. Deliberately data, not code (spec 37).
ROUTING = {
    "infrastructure/roads": "municipal-corporation/road-department",
    "infrastructure/streetlights": "municipal-corporation/streetlight-department",
    "infrastructure/bridges": "public-works-department/highways-wing",
    "infrastructure/footpaths": "municipal-corporation/road-department",
    "water-sanitation/water-supply": "municipal-corporation/water-department",
    "water-sanitation/drainage": "municipal-corporation/water-department",
    "water-sanitation/sewage": "municipal-corporation/sanitation-department",
    "waste-management": "municipal-corporation/sanitation-department",
    "healthcare": "health-department",
    "healthcare/hospitals": "health-department/hospital-administration",
    "education": "education-department",
    "education/schools": "education-department/school-education",
    "electricity": "electricity-board",
    "electricity/power-supply": "electricity-board/distribution",
    "environment": "pollution-control-board",
    "transport": "transport-department",
    "transport/traffic-management": "transport-department/traffic-police",
}


class Command(BaseCommand):
    help = "Seed categories, departments and routing rules."

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        categories = self._seed_categories()
        departments = self._seed_departments()
        rules = self._seed_routing()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {categories} categories, {departments} departments, {rules} routing rules."
            )
        )

    def _seed_categories(self) -> int:
        count = 0
        for order, (parent_name, children) in enumerate(CATEGORY_TREE.items()):
            parent, created = Category.objects.get_or_create(
                name=parent_name, parent=None, defaults={"display_order": order * 10}
            )
            count += int(created)
            for child_order, child_name in enumerate(children):
                _, child_created = Category.objects.get_or_create(
                    name=child_name, parent=parent, defaults={"display_order": child_order}
                )
                count += int(child_created)
        return count

    def _seed_departments(self) -> int:
        count = 0
        for order, (name, level, wings) in enumerate(DEPARTMENTS):
            parent, created = Department.objects.get_or_create(
                name=name, parent=None, defaults={"level": level, "display_order": order * 10}
            )
            count += int(created)
            for wing_order, wing in enumerate(wings):
                _, wing_created = Department.objects.get_or_create(
                    name=wing,
                    parent=parent,
                    defaults={"level": level, "display_order": wing_order},
                )
                count += int(wing_created)
        return count

    def _seed_routing(self) -> int:
        count = 0
        for category_path, department_path in ROUTING.items():
            category = Category.objects.filter(path=category_path).first()
            department = Department.objects.filter(path=department_path).first()
            if not (category and department):
                self.stderr.write(f"skipped routing {category_path} -> {department_path}")
                continue
            _, created = RoutingRule.objects.get_or_create(
                category=category, department=department, state="", district="", city=""
            )
            count += int(created)
        return count
