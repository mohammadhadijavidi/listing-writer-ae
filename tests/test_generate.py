import json

import pytest

from listing_writer_ae import write_listing
from listing_writer_ae.checks import check_claims
from listing_writer_ae.generate import FIELDS, build_prompt, compliance_footer, hashtags, parse_json, render_text, safe_highlights
from listing_writer_ae.providers import ProviderError


class FakeLLM:
    """Scripted stand-in for an LLM, used to test the revise loop. Not a model."""

    name = "fake"
    model = "scripted"
    is_mock = False

    def __init__(self, replies):
        self.replies = list(replies)
        self.prompts = []

    def complete(self, prompt, max_tokens=2500):
        self.prompts.append(prompt)
        return self.replies.pop(0)


def reply(**over):
    base = {
        "title_en": "2-Bedroom Apartment for Sale in Dubai Marina",
        "title_ar": "شقة من غرفتي نوم للبيع في دبي مارينا",
        "description_en": "A 2-bedroom apartment in Dubai Marina with 1,240 sq ft and a marina view. AED 2,450,000.",
        "description_ar": "شقة من غرفتي نوم في دبي مارينا بمساحة 1,240 قدم مربع وإطلالة على المارينا. 2,450,000 درهم.",
        "social_en": "2BR in Dubai Marina, marina view. AED 2,450,000.",
        "social_ar": "شقة من غرفتي نوم في دبي مارينا. 2,450,000 درهم.",
    }
    base.update(over)
    return json.dumps(base, ensure_ascii=False)


def test_mock_writes_all_fields_and_labels_itself(sample):
    lst = write_listing(sample("01"), "mock")
    for f in FIELDS:
        assert getattr(lst, f).strip()
    assert lst.written_by == "mock (template writer, no LLM)"
    assert lst.sample is True


def test_mock_output_is_deterministic(sample):
    assert write_listing(sample("01"), "mock").to_dict() == write_listing(sample("01"), "mock").to_dict()


@pytest.mark.parametrize("prefix", ["01", "02", "03", "04"])
def test_mock_output_never_contains_claims(sample, prefix):
    lst = write_listing(sample(prefix), "mock")
    out = [f for f in lst.findings if not f.where.startswith("input:") and f.category in ("claim", "consistency")]
    assert out == [], [(f.code, f.where, f.match) for f in out]


def test_risky_highlights_are_dropped_not_published(sample):
    lst = write_listing(sample("01"), "mock")
    assert any("Guaranteed" in d for d in lst.dropped_highlights)
    assert any("أفضل سعر" in d for d in lst.dropped_highlights)
    assert "Guaranteed" not in lst.description_en and "أفضل" not in lst.description_ar
    assert "Upgraded kitchen" in lst.description_en and "مطبخ" in lst.description_ar
    assert lst.ready_to_publish  # input-only errors do not block


def test_safe_highlights_split():
    keep, drop = safe_highlights("Upgraded kitchen. Guaranteed 10% ROI! Near the tram.")
    assert keep == ["Upgraded kitchen.", "Near the tram."]
    assert drop == ["Guaranteed 10% ROI!"]


def test_footer_written_by_code(sample):
    en, ar = compliance_footer(sample("01"))
    assert "Permit No.: SAMPLE-0000000000" in en and "رقم التصريح: \u2066SAMPLE-0000000000\u2069" in ar
    assert "Sample Realty LLC" in en and "Sample Realty LLC" in ar
    assert "QR" in en


def test_off_plan_footer_and_findings(sample):
    p = sample("03")
    en, _ = compliance_footer(p)
    assert "Developer: Sample Developments" in en and "Project No.: SAMPLE-P-0001" in en
    lst = write_listing(p, "mock")
    assert "Off-Plan" in lst.title_en and "على المخطط" in lst.title_ar
    assert "Q4 2027" in lst.description_en
    assert not lst.ready_to_publish
    assert {"LW-P04", "LW-P05"} <= {f.code for f in lst.findings}


def test_missing_permit_blocks_publishing(sample):
    lst = write_listing(sample("02"), "mock")
    assert not lst.ready_to_publish
    assert "LW-P01" in {f.code for f in lst.findings}
    # the data-level finding is not duplicated per output field
    assert sum(f.code == "LW-P01" for f in lst.findings) == 1
    assert "LW-P02" not in {f.code for f in lst.findings}


def test_compliant_sample_is_ready(sample):
    lst = write_listing(sample("04"), "mock")
    assert lst.ready_to_publish and lst.summary == {"error": 0, "warning": 0, "info": 0}


def test_arabic_grammar_in_template(sample):
    lst = write_listing(sample("01"), "mock")
    assert "من غرفتي نوم" in lst.title_ar  # genitive dual after "من"
    assert "غير مفروشة" in lst.description_ar  # feminine agreement with شقة
    studio = write_listing(sample("02"), "mock")
    assert "استوديو مفروش" in studio.description_ar  # masculine
    assert "4 شيكات" in studio.social_ar


def test_hashtags(sample):
    tags = hashtags(sample("01"))
    assert "#DubaiMarina" in tags and "#دبي_مارينا" in tags and len(tags) == len(set(tags))


def test_render_text_contains_both_languages(sample):
    txt = render_text(write_listing(sample("01"), "mock"))
    assert "Permit No.:" in txt and "رقم التصريح:" in txt


# ---------------------------------------------------------------- LLM path (scripted fake, no network)

def test_llm_path_clean_reply(sample):
    llm = FakeLLM([reply()])
    lst = write_listing(sample("01"), llm)
    assert lst.written_by == "fake (scripted)" and lst.revisions == 0
    assert lst.footer_en.startswith("Permit No.:")  # appended by code even though the model did not write it
    assert not [f for f in lst.findings if not f.where.startswith("input:")]


def test_prompt_contains_only_safe_notes_and_no_permit(sample):
    llm = FakeLLM([reply()])
    write_listing(sample("01"), llm)
    user = llm.prompts[0].user
    assert "Upgraded kitchen" in user and "Guaranteed" not in user and "أفضل سعر" not in user
    assert "SAMPLE-0000000000" not in user


def test_llm_revision_loop_fixes_claims(sample):
    bad = reply(description_en="Best price in Marina! Guaranteed 9% ROI. 3 bedroom apartment, 1,240 sq ft. AED 2,450,000.")
    llm = FakeLLM([bad, reply()])
    lst = write_listing(sample("01"), llm, max_revisions=1)
    assert lst.revisions == 1 and len(llm.prompts) == 2
    fb = llm.prompts[1].user
    assert "LW-C01" in fb and "LW-D01" in fb
    assert not [f for f in lst.findings if not f.where.startswith("input:")]


def test_llm_still_bad_after_revisions_is_reported(sample):
    bad = reply(social_en="Risk-free! Prices will double. AED 2,450,000")
    lst = write_listing(sample("01"), FakeLLM([bad, bad]), max_revisions=1)
    assert not lst.ready_to_publish
    assert {"LW-C03", "LW-C04"} <= {f.code for f in lst.findings if f.where == "social_en"}


def test_parse_json_variants():
    assert parse_json("```json\n" + reply() + "\n```")["title_en"]
    assert parse_json("Here you go: " + reply() + " thanks")["social_ar"]
    with pytest.raises(ProviderError):
        parse_json("no json here")
    with pytest.raises(ProviderError):
        parse_json('{"title_en": "x"}')


def test_build_prompt_has_rules_and_feedback(sample):
    p = build_prompt(sample("01"), ["Upgraded kitchen."], [], feedback=check_claims("Guaranteed ROI"))
    assert "Do not add amenities" in p.system and "guarantee" in p.system.lower()
    assert "LW-C01" in p.user and "دبي مارينا" in p.user
