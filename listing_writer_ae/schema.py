"""Property input schema (plain dataclass, no dependencies) and loading/validation helpers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

PURPOSES = ("sale", "rent")
STATUSES = ("ready", "off_plan")
FURNISHING = ("furnished", "unfurnished", "partly_furnished")
PROPERTY_TYPES = (
    "apartment",
    "studio",
    "villa",
    "townhouse",
    "penthouse",
    "duplex",
    "hotel_apartment",
    "office",
    "retail",
    "warehouse",
    "land",
)
RENT_PERIODS = ("yearly", "monthly")


class PropertyError(ValueError):
    """Raised when property data is missing required fields or has invalid values."""


@dataclass
class Property:
    # What is being advertised
    purpose: str = "sale"  # sale | rent
    property_type: str = "apartment"
    status: str = "ready"  # ready | off_plan
    community: str = ""  # e.g. "Dubai Marina"
    community_ar: str = ""  # optional Arabic name override
    building: str = ""  # building / tower / cluster name (optional)
    bedrooms: int | None = None  # 0 = studio
    bathrooms: int | None = None
    size_sqft: float | None = None
    price_aed: float | None = None  # sale price, or rent per rent_period
    rent_period: str = "yearly"
    cheques: int | None = None  # rent only: number of cheques accepted
    furnishing: str = "unfurnished"
    view: str = ""
    view_ar: str = ""
    floor: str = ""
    parking: int | None = None
    features: list[str] = field(default_factory=list)
    features_ar: list[str] = field(default_factory=list)  # optional, same order as features
    highlights: str = ""  # free-text facts from the agent, English (checked for claims before use)
    highlights_ar: str = ""  # same, Arabic (optional)

    # Who is advertising
    company_name: str = ""
    company_orn: str = ""  # office registration number (optional, shown if given)
    agent_name: str = ""
    agent_brn: str = ""  # broker registration number (optional, shown if given)
    agent_phone: str = ""

    # Permits (Dubai Land Department / RERA, via the Trakheesi system)
    permit_number: str = ""  # advertising permit number from Trakheesi
    qr_code_ready: bool = False  # True once you have the DLD-issued QR code for this ad
    promotions: list[str] = field(default_factory=list)  # e.g. "DLD fee waiver", "2% discount"
    promo_permit_number: str = ""  # separate permit for promotional campaigns

    # Off-plan only (RERA Circular 2-2022, item 3)
    developer: str = ""
    project_name: str = ""
    project_number: str = ""
    project_location: str = ""
    escrow_account: str = ""
    handover: str = ""  # e.g. "Q4 2027" (as stated by the developer)

    # Labelling for demos
    sample: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Property:
        if not isinstance(data, dict):
            raise PropertyError("property data must be a JSON object")
        known = {f.name for f in fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise PropertyError(f"unknown field(s): {', '.join(unknown)}")
        prop = cls(**data)
        prop.normalise()
        prop.validate()
        return prop

    @classmethod
    def load(cls, path: str | Path) -> Property:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise PropertyError(f"{path}: invalid JSON ({e})") from e
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    # ------------------------------------------------------------------ helpers
    def normalise(self) -> None:
        for name in ("purpose", "property_type", "status", "furnishing", "rent_period"):
            v = getattr(self, name)
            if isinstance(v, str):
                setattr(self, name, v.strip().lower().replace("-", "_").replace(" ", "_"))
        if self.property_type == "studio" and self.bedrooms is None:
            self.bedrooms = 0
        for name in ("bedrooms", "bathrooms", "parking", "cheques"):
            v = getattr(self, name)
            if v is not None and not isinstance(v, bool):
                try:
                    setattr(self, name, int(v))
                except (TypeError, ValueError) as e:
                    raise PropertyError(f"{name} must be a whole number") from e
        for name in ("size_sqft", "price_aed"):
            v = getattr(self, name)
            if v is not None:
                try:
                    setattr(self, name, float(str(v).replace(",", "")))
                except ValueError as e:
                    raise PropertyError(f"{name} must be a number") from e
        for name in ("features", "features_ar", "promotions"):
            v = getattr(self, name)
            if isinstance(v, str):
                setattr(self, name, [s.strip() for s in v.split(",") if s.strip()])
            elif v is None:
                setattr(self, name, [])
        for f in fields(self):
            v = getattr(self, f.name)
            if isinstance(v, str):
                setattr(self, f.name, v.strip())

    def validate(self) -> None:
        if self.purpose not in PURPOSES:
            raise PropertyError(f"purpose must be one of {PURPOSES}")
        if self.status not in STATUSES:
            raise PropertyError(f"status must be one of {STATUSES}")
        if self.property_type not in PROPERTY_TYPES:
            raise PropertyError(f"property_type must be one of {PROPERTY_TYPES}")
        if self.furnishing not in FURNISHING:
            raise PropertyError(f"furnishing must be one of {FURNISHING}")
        if self.rent_period not in RENT_PERIODS:
            raise PropertyError(f"rent_period must be one of {RENT_PERIODS}")
        if not self.community:
            raise PropertyError("community is required (e.g. 'Dubai Marina')")
        if self.price_aed is None or self.price_aed <= 0:
            raise PropertyError("price_aed is required and must be positive")
        if self.size_sqft is not None and self.size_sqft <= 0:
            raise PropertyError("size_sqft must be positive")
        for name in ("bedrooms", "bathrooms", "parking", "cheques"):
            v = getattr(self, name)
            if v is not None and v < 0:
                raise PropertyError(f"{name} cannot be negative")
        if self.features_ar and len(self.features_ar) != len(self.features):
            raise PropertyError("features_ar must have the same length and order as features")

    @property
    def is_off_plan(self) -> bool:
        return self.status == "off_plan"

    @property
    def is_rent(self) -> bool:
        return self.purpose == "rent"
