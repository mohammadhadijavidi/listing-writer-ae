import pytest

from listing_writer_ae import Property, check_text
from listing_writer_ae.checks import check_claims, check_inputs, check_property, mentions_promotion, summarise
from listing_writer_ae.sources import SOURCES


def codes(findings):
    return {f.code for f in findings}


# ---------------------------------------------------------------- claims, English and Arabic

@pytest.mark.parametrize(
    "text,code",
    [
        ("Guaranteed 8% ROI for investors", "LW-C01"),
        ("8% net yield guaranteed for 3 years", "LW-C01"),
        ("assured rental income", "LW-C01"),
        ("عائد إيجاري مضمون 8٪", "LW-C01"),
        ("عائد سنوي ثابت", "LW-C01"),
        ("ضمان العائد لمدة 5 سنوات", "LW-C01"),
        ("Best price in the Marina", "LW-C02"),
        ("the cheapest 2BR in JVC", "LW-C02"),
        ("Unbeatable location", "LW-C02"),
        ("أفضل سعر في المارينا", "LW-C02"),
        ("أرخص شقة في المنطقة", "LW-C02"),
        ("لا مثيل له", "LW-C02"),
        ("Risk-free investment", "LW-C03"),
        ("zero risk", "LW-C03"),
        ("استثمار بدون مخاطر", "LW-C03"),
        ("ربح أكيد", "LW-C03"),
        ("Prices will double by 2028", "LW-C04"),
        ("الأسعار سترتفع قريباً", "LW-C04"),
        ("Hurry, last unit left!", "LW-C05"),
        ("once-in-a-lifetime opportunity", "LW-C05"),
        ("فرصة لا تتكرر", "LW-C05"),
        ("سارع بالحجز", "LW-C05"),
        ("Priced below market value", "LW-C06"),
        ("أقل من سعر السوق", "LW-C06"),
        ("Golden Visa eligible", "LW-C07"),
        ("الإقامة الذهبية", "LW-C07"),
        ("5 minutes from Dubai Mall", "LW-C08"),
        ("5 دقائق من دبي مول", "LW-C08"),
        ("JUST SOLD in Marina", "LW-C09"),
        ("تم البيع", "LW-C09"),
    ],
)
def test_claim_rules_fire(text, code):
    assert code in codes(check_claims(text))


@pytest.mark.parametrize(
    "text",
    [
        "Bright 2-bedroom apartment with a balcony and a marina view.",
        "شقة مشرقة من غرفتي نوم مع شرفة وإطلالة على المارينا.",
        "Built in 2019. Service charge AED 18 per sq ft (2025).",
        "Close to the tram stop.",
        "Freehold apartment in a gated community.",
    ],
)
def test_neutral_copy_has_no_claim_findings(text):
    assert check_claims(text) == []


def test_arabic_match_returns_original_spelling_with_diacritics():
    f = check_claims("عائدٌ مضمونٌ")[0]
    assert f.code == "LW-C01"
    assert "مضمون" in f.match and "عائد" in f.match


def test_heuristic_basis_and_sources_exist():
    for f in check_claims("Guaranteed ROI, best price, risk-free, prices will double, hurry, golden visa, just sold"):
        assert f.basis == "heuristic"
        for k in f.sources:
            assert k in SOURCES


# ---------------------------------------------------------------- promotions

@pytest.mark.parametrize("text", ["Free DLD registration", "2% discount this month", "DLD fee waiver", "خصم 5٪", "إعفاء من رسوم التسجيل", "No agency fee"])
def test_promotions_detected(text):
    assert mentions_promotion(text)


@pytest.mark.parametrize("text", ["Freehold", "chiller free", "Chiller-free", "free zone company", "risk-free", "تبريد مجاني"])
def test_promotion_false_friends_ignored(text):
    assert mentions_promotion(text) is None


def test_promotion_in_text_without_promo_permit_is_error(clean_prop):
    text = "Free DLD registration! Permit No.: 7123456789 Test Realty"
    f = [x for x in check_text(text, clean_prop) if x.code == "LW-P05"]
    assert f and f[0].severity == "error"


def test_promotion_without_property_is_warning():
    f = [x for x in check_text("Free DLD registration") if x.code == "LW-P05"]
    assert f and f[0].severity == "warning"


# ---------------------------------------------------------------- property-level compliance

def test_clean_property_has_no_findings(clean_prop):
    assert check_property(clean_prop) == []


@pytest.mark.parametrize("permit", ["", "TBD", "n/a", "0000", "xxx"])
def test_missing_or_placeholder_permit(clean_prop, permit):
    clean_prop.permit_number = permit
    f = [x for x in check_property(clean_prop) if x.code == "LW-P01"]
    assert f and f[0].severity == "error" and "rera-circular-2-2022" in f[0].sources


def test_missing_company(clean_prop):
    clean_prop.company_name = ""
    assert "LW-P03" in codes(check_property(clean_prop))


def test_qr_not_ready_is_warning(clean_prop):
    clean_prop.qr_code_ready = False
    f = [x for x in check_property(clean_prop) if x.code == "LW-P06"][0]
    assert f.severity == "warning" and "dld-2024-qr" in f.sources


def test_off_plan_particulars(sample):
    p = sample("03")  # sample deliberately misses the escrow account and has a promo without permit
    found = codes(check_property(p))
    assert {"LW-P04", "LW-P05"} <= found
    msg = [x for x in check_property(p) if x.code == "LW-P04"][0].message_en
    assert "escrow" in msg and "developer" not in msg


def test_off_plan_complete_passes(sample):
    p = sample("03")
    p.escrow_account = "SAMPLE-ESCROW-1"
    p.promo_permit_number = "SAMPLE-PROMO-1"
    assert check_property(p) == []


def test_check_inputs_flags_agent_highlights(sample):
    f = check_inputs(sample("01"))
    assert {"LW-C01", "LW-C02"} <= codes(f)
    assert {x.where for x in f} >= {"input:highlights", "input:highlights_ar"}


# ---------------------------------------------------------------- consistency with the data

def test_consistency_catches_wrong_facts(clean_prop):
    text = "Spacious 3 bedroom apartment, 1,500 sq ft, AED 2.2M, fully furnished, private pool, off-plan."
    found = codes(check_text(text, clean_prop, require_footer=False))
    assert {"LW-D01", "LW-D02", "LW-D03", "LW-D05", "LW-D06", "LW-D04"} <= found


def test_consistency_arabic(clean_prop):
    text = "شقة من 3 غرف نوم بمساحة ١٬٥٠٠ قدم مربع بسعر ٢٬٢٠٠٬٠٠٠ درهم مع مسبح خاص"
    found = codes(check_text(text, clean_prop, require_footer=False))
    assert {"LW-D01", "LW-D02", "LW-D03", "LW-D06"} <= found


def test_consistency_accepts_correct_facts(clean_prop):
    text = "1-bedroom apartment in Business Bay, 800 sq ft, AED 1,300,000. Unfurnished. Balcony and gym."
    assert check_text(text, clean_prop, require_footer=False) == []
    text_ar = "شقة غير مفروشة من غرفة نوم واحدة، 800 قدم مربع، 1,300,000 درهم."
    assert check_text(text_ar, clean_prop, require_footer=False) == []


def test_price_accepts_scaled_and_rent_variants():
    rent = Property.from_dict({"purpose": "rent", "community": "JVC", "price_aed": 60000, "cheques": 4, "bedrooms": 0, "property_type": "studio"})
    for ok in ["AED 60,000 per year", "AED 60k", "AED 5,000 per month", "AED 15,000 per cheque", "60,000 درهم"]:
        assert "LW-D03" not in codes(check_text(ok, rent, require_footer=False)), ok
    assert "LW-D03" in codes(check_text("AED 50,000 per year", rent, require_footer=False))


def test_feature_claim_supported_by_data_is_fine(sample):
    villa = sample("04")
    assert "LW-D06" not in codes(check_text("Villa with a private pool and private beach. Sea view.", villa, require_footer=False))


def test_off_plan_ready_to_move_contradiction(sample):
    p = sample("03")
    assert "LW-D04" in codes(check_text("Ready to move in townhouse", p, require_footer=False))
    assert "LW-D04" in codes(check_text("تاون هاوس جاهز للسكن", p, require_footer=False))


def test_unfurnished_negation_not_flagged(clean_prop):
    assert "LW-D05" not in codes(check_text("Unfurnished apartment. شقة غير مفروشة.", clean_prop, require_footer=False))


# ---------------------------------------------------------------- required particulars in published text

def test_ad_text_must_carry_permit_and_company(clean_prop):
    found = codes(check_text("Nice 1-bedroom apartment.", clean_prop))
    assert {"LW-P02", "LW-P03"} <= found
    ok = check_text("Nice 1-bedroom apartment. Permit No.: 712 345 6789. Test Realty.", clean_prop)
    assert not ({"LW-P02", "LW-P03"} & codes(ok))


def test_permit_matching_ignores_arabic_digits(clean_prop):
    assert "LW-P02" not in codes(check_text("رقم التصريح: ٧١٢٣٤٥٦٧٨٩ — Test Realty", clean_prop))


# ---------------------------------------------------------------- style

def test_style_shouting_and_exclamations():
    found = codes(check_text("AMAZING HUGE APARTMENT WITH STUNNING VIEWS AND MASSIVE BALCONY NOW!!!"))
    assert {"LW-S01", "LW-S02"} <= found


def test_summary_and_ordering():
    f = check_text("Golden Visa! Best price. Guaranteed ROI.")
    assert [x.severity for x in f] == sorted([x.severity for x in f], key=["error", "warning", "info"].index)
    assert summarise(f) == {"error": 1, "warning": 1, "info": 1}


def test_findings_bilingual():
    for f in check_text("Guaranteed ROI, best price, hurry, golden visa, 5 minutes from the mall!!!"):
        assert f.message_en and f.message_ar
