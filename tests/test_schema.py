import pytest

from listing_writer_ae import Property, PropertyError


def test_samples_load_and_are_labelled(sample):
    for prefix in ("01", "02", "03", "04"):
        p = sample(prefix)
        assert p.sample is True
        assert p.permit_number == "" or p.permit_number.startswith("SAMPLE")


def test_normalises_strings_and_numbers():
    p = Property.from_dict(
        {"purpose": " Rent ", "property_type": "Hotel Apartment", "status": "off-plan", "community": "JVC",
         "price_aed": "85,000", "bedrooms": "2", "features": "Balcony, Gym ,", "developer": "D", "project_name": "P"}
    )
    assert p.purpose == "rent" and p.property_type == "hotel_apartment" and p.status == "off_plan"
    assert p.price_aed == 85000.0 and p.bedrooms == 2 and p.features == ["Balcony", "Gym"]


def test_studio_defaults_to_zero_bedrooms():
    assert Property.from_dict({"property_type": "studio", "community": "JLT", "price_aed": 1}).bedrooms == 0


@pytest.mark.parametrize(
    "bad",
    [
        {"community": "X"},  # no price
        {"price_aed": 1},  # no community
        {"community": "X", "price_aed": -5},
        {"community": "X", "price_aed": 1, "purpose": "lease"},
        {"community": "X", "price_aed": 1, "property_type": "castle"},
        {"community": "X", "price_aed": 1, "bedrooms": -1},
        {"community": "X", "price_aed": 1, "bedrooms": "two"},
        {"community": "X", "price_aed": 1, "nonsense": True},
        {"community": "X", "price_aed": 1, "features": ["a", "b"], "features_ar": ["أ"]},
    ],
)
def test_rejects_invalid(bad):
    with pytest.raises(PropertyError):
        Property.from_dict(bad)


def test_rejects_non_object():
    with pytest.raises(PropertyError):
        Property.from_dict(["x"])
