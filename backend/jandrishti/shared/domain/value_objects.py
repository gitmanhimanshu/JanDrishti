"""
Value objects shared across modules.

These are immutable, self-validating and free of any framework import. A
GeoPoint that exists is a valid GeoPoint -- callers never have to re-check it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from .exceptions import ValidationError

EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True, slots=True)
class GeoPoint:
    """A WGS84 coordinate pair.

    Deliberately not GeoDjango: JanDrishti needs proximity search over points,
    not arbitrary geometry, and a lat/lng pair with a bounding-box prefilter
    plus a haversine refine keeps the deployment free of a GDAL dependency.
    See docs/decisions/database.md.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise ValidationError("Latitude must be between -90 and 90.")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValidationError("Longitude must be between -180 and 180.")

    def distance_km(self, other: GeoPoint) -> float:
        """Great-circle distance to another point, in kilometres."""
        lat1, lon1, lat2, lon2 = map(
            math.radians, (self.latitude, self.longitude, other.latitude, other.longitude)
        )
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))

    def distance_m(self, other: GeoPoint) -> float:
        return self.distance_km(other) * 1000.0

    def bounding_box(self, radius_km: float) -> tuple[float, float, float, float]:
        """(min_lat, max_lat, min_lng, max_lng) enclosing a radius.

        Used as a cheap index-friendly prefilter before the exact haversine
        check, so proximity queries never scan the whole table.
        """
        lat_delta = radius_km / 111.32
        cos_lat = math.cos(math.radians(self.latitude))
        # Near the poles the longitude degree shrinks to nothing; clamp so the
        # box stays finite instead of exploding to the whole planet.
        lng_delta = radius_km / max(111.32 * cos_lat, 0.0001)
        return (
            max(self.latitude - lat_delta, -90.0),
            min(self.latitude + lat_delta, 90.0),
            max(self.longitude - lng_delta, -180.0),
            min(self.longitude + lng_delta, 180.0),
        )

    @classmethod
    def parse(cls, latitude: object, longitude: object) -> GeoPoint | None:
        """Build a point from untrusted input; None when either half is absent."""
        if latitude in (None, "") or longitude in (None, ""):
            return None
        try:
            return cls(float(latitude), float(longitude))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ValidationError("Coordinates must be numeric.") from exc


@dataclass(frozen=True, slots=True)
class Location:
    """Where a problem is, in the terms Indian administration actually uses."""

    address: str = ""
    city: str = ""
    district: str = ""
    state: str = ""
    pincode: str = ""
    point: GeoPoint | None = None

    PINCODE_RE = re.compile(r"^[1-9][0-9]{5}$")

    def __post_init__(self) -> None:
        if self.pincode and not self.PINCODE_RE.match(self.pincode):
            raise ValidationError("Pincode must be six digits and not start with zero.")
        if not (self.state or self.point):
            raise ValidationError("A location needs at least a state or GPS coordinates.")

    @property
    def display(self) -> str:
        parts = [p for p in (self.city, self.district, self.state) if p]
        return ", ".join(dict.fromkeys(parts))


@dataclass(frozen=True, slots=True)
class Money:
    """Rupee amount. Integer paise internally -- floats never touch money."""

    amount: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValidationError("Amount cannot be negative.")
        if self.currency != "INR":
            raise ValidationError("Only INR is supported.")

    @classmethod
    def of(cls, value: object) -> Money:
        try:
            return cls(Decimal(str(value)))
        except (InvalidOperation, TypeError) as exc:
            raise ValidationError("Amount is not a valid number.") from exc

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        return Money(self.amount - other.amount, self.currency)
