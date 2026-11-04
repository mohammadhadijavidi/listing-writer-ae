"""Check an ad you already wrote (Arabic or English) against the property data. No LLM involved."""

from listing_writer_ae import Property, check_text

prop = Property.from_dict(
    {
        "sample": True,
        "purpose": "sale",
        "property_type": "apartment",
        "community": "Business Bay",
        "bedrooms": 1,
        "size_sqft": 780,
        "price_aed": 1_250_000,
        "features": ["Balcony", "Gym"],
        "company_name": "Sample Realty LLC",
        "permit_number": "SAMPLE-3333333333",
        "qr_code_ready": True,
    }
)

ad = """شقة فاخرة من غرفتي نوم في الخليج التجاري مع مسبح خاص!!
عائد إيجاري مضمون 9٪ وأفضل سعر في المنطقة. سارع، آخر وحدة!
السعر ١٬١٠٠٬٠٠٠ درهم فقط. إعفاء من رسوم الدائرة."""

for f in check_text(ad, prop):
    print(f"{f.severity:7} {f.code}  {f.message_ar}  «{f.match}»")
