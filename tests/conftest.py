import json
from pathlib import Path

import pytest

from listing_writer_ae import Property

SAMPLES = Path(__file__).resolve().parent.parent / "listing_writer_ae" / "samples"


@pytest.fixture
def sample():
    def load(prefix: str) -> Property:
        path = next(SAMPLES.glob(prefix + "*.json"))
        return Property.load(path)

    return load


@pytest.fixture
def clean_prop():
    """A fully compliant ready apartment (no findings expected)."""
    return Property.from_dict(
        {
            "purpose": "sale",
            "property_type": "apartment",
            "community": "Business Bay",
            "bedrooms": 1,
            "bathrooms": 2,
            "size_sqft": 800,
            "price_aed": 1_300_000,
            "features": ["Balcony", "Gym"],
            "company_name": "Test Realty",
            "permit_number": "7123456789",
            "qr_code_ready": True,
        }
    )


@pytest.fixture
def raw_sample():
    def load(prefix: str) -> dict:
        return json.loads(next(SAMPLES.glob(prefix + "*.json")).read_text(encoding="utf-8"))

    return load
