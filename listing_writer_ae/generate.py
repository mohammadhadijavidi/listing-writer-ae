"""Turn property data into a bilingual listing: portal title + description and a social post, in Arabic and English.

Pipeline
--------
1. ``check_inputs``: data-level compliance (permit, company, off-plan particulars, promo permit, QR) and claim
   checks on the agent's free-text highlights. Highlight sentences that trip a claim rule are *kept out* of
   the draft.
2. Writer: an LLM (any provider from ``providers.py``) or, with ``mock``, a deterministic bilingual template.
   The LLM only receives facts and is told not to add any.
3. The compliance footer (permit number, company, ORN/BRN, off-plan particulars) is appended *by code*,
   never by the model, so it cannot be paraphrased away or hallucinated.
4. ``check_text`` on every output field: claims, consistency with the data, required particulars, style.
5. LLM only: if step 4 finds errors, one revision round with the findings fed back, then re-check.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

from . import glossary as g
from .checks import Finding, check_claims, check_inputs, check_text, sort_findings, summarise
from .providers import Prompt, ProviderError, get_provider
from .schema import Property

TITLE_MAX = 80  # project default; check your portal's own limit
FIELDS = ("title_en", "title_ar", "description_en", "description_ar", "social_en", "social_ar")


@dataclass
class Listing:
    title_en: str = ""
    title_ar: str = ""
    description_en: str = ""
    description_ar: str = ""
    social_en: str = ""
    social_ar: str = ""
    hashtags: list[str] = field(default_factory=list)
    footer_en: str = ""
    footer_ar: str = ""
    findings: list[Finding] = field(default_factory=list)
    written_by: str = ""
    dropped_highlights: list[str] = field(default_factory=list)
    revisions: int = 0
    sample: bool = False

    @property
    def summary(self) -> dict[str, int]:
        return summarise(self.findings)

    @property
    def ready_to_publish(self) -> bool:
        """No errors in the data or in the generated text.

        Findings on the agent's own notes (``where`` starting with ``input:``) do not block: the flagged
        sentences were kept out of the draft (see ``dropped_highlights``).
        """
        return not any(f.severity == "error" and not f.where.startswith("input:") for f in self.findings)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        d["summary"] = self.summary
        d["ready_to_publish"] = self.ready_to_publish
        return d


# --------------------------------------------------------------------------- formatting helpers


def ltr(s: str) -> str:
    """Wrap a Latin/number run in Unicode directional isolates (LRI ... PDI) for use inside Arabic text,
    so phone numbers like "+971 50 ..." are not reordered by the bidi algorithm."""
    return f"\u2066{s}\u2069" if s else s


def fmt_aed(v: float) -> str:
    return f"{v:,.0f}"


def fmt_size(v: float | None) -> str:
    return f"{v:,.0f}" if v else ""


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!؟?\n])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def safe_highlights(text: str) -> tuple[list[str], list[str]]:
    """Split free-text highlights into sentences that pass claim checks and ones that don't."""
    keep, drop = [], []
    for s in _split_sentences(text):
        (drop if check_claims(s) else keep).append(s)
    return keep, drop


def type_words(prop: Property) -> tuple[str, str]:
    return g.PROPERTY_TYPE.get(prop.property_type, (prop.property_type.title(), prop.property_type))


def furnishing_words(prop: Property) -> tuple[str, str]:
    en, ar_f, ar_m = g.FURNISHING[prop.furnishing]
    return en, (ar_f if prop.property_type in g.FEMININE_TYPES else ar_m)


def furnishing_words_masc(prop: Property) -> str:
    return g.FURNISHING[prop.furnishing][2]


def price_phrase(prop: Property) -> tuple[str, str]:
    p = fmt_aed(prop.price_aed or 0)
    if prop.is_rent:
        per_en = "per year" if prop.rent_period == "yearly" else "per month"
        per_ar = "سنوياً" if prop.rent_period == "yearly" else "شهرياً"
        en, ar = f"AED {p} {per_en}", f"{p} درهم {per_ar}"
        if prop.cheques:
            en += f" ({prop.cheques} cheque{'s' if prop.cheques != 1 else ''})"
            ar += f" ({g.cheques_ar(prop.cheques)})"
        return en, ar
    return f"AED {p}", f"{p} درهم"


def compliance_footer(prop: Property) -> tuple[str, str]:
    """Required particulars, written by code. Empty values are simply omitted (the checker flags them)."""
    en: list[str] = []
    ar: list[str] = []
    if prop.permit_number:
        en.append(f"Permit No.: {prop.permit_number}")
        ar.append(f"رقم التصريح: {ltr(prop.permit_number)}")
    if prop.company_name:
        orn_en = f" (ORN {prop.company_orn})" if prop.company_orn else ""
        orn_ar = f" (رقم تسجيل المكتب {prop.company_orn})" if prop.company_orn else ""
        en.append(f"Listed by {prop.company_name}{orn_en}")
        ar.append(f"المعلن: {ltr(prop.company_name)}{orn_ar}")
    if prop.agent_name:
        brn_en = f", BRN {prop.agent_brn}" if prop.agent_brn else ""
        brn_ar = f"، رقم تسجيل الوسيط {prop.agent_brn}" if prop.agent_brn else ""
        phone = f", {prop.agent_phone}" if prop.agent_phone else ""
        en.append(f"Agent: {prop.agent_name}{brn_en}{phone}")
        ar.append(f"الوسيط: {ltr(prop.agent_name)}{brn_ar}{('، ' + ltr(prop.agent_phone)) if prop.agent_phone else ''}")
    if prop.is_off_plan:
        bits_en, bits_ar = [], []
        if prop.developer:
            bits_en.append(f"Developer: {prop.developer}")
            bits_ar.append(f"المطوّر: {ltr(prop.developer)}")
        if prop.project_name:
            bits_en.append(f"Project: {prop.project_name}")
            bits_ar.append(f"المشروع: {ltr(prop.project_name)}")
        if prop.project_number:
            bits_en.append(f"Project No.: {prop.project_number}")
            bits_ar.append(f"رقم المشروع: {ltr(prop.project_number)}")
        if prop.project_location:
            bits_en.append(f"Location: {prop.project_location}")
            bits_ar.append(f"الموقع: {ltr(prop.project_location)}")
        if prop.escrow_account:
            bits_en.append(f"Escrow A/C: {prop.escrow_account}")
            bits_ar.append(f"حساب الضمان: {ltr(prop.escrow_account)}")
        if bits_en:
            en.append(" | ".join(bits_en))
            ar.extend(bits_ar)
    if prop.promotions and prop.promo_permit_number:
        en.append(f"Promotion permit No.: {prop.promo_permit_number}")
        ar.append(f"رقم تصريح الحملة الترويجية: {ltr(prop.promo_permit_number)}")
    if prop.qr_code_ready:
        en.append("Scan the DLD permit QR code on this listing to verify it.")
        ar.append("امسح رمز QR الخاص بتصريح الدائرة في هذا الإعلان للتحقق منه.")
    return "\n".join(en), "\n".join(ar)


def hashtags(prop: Property) -> list[str]:
    t_en, _ = type_words(prop)
    tags = ["#Dubai", "#DubaiRealEstate", f"#{re.sub(r'[^A-Za-z0-9]', '', prop.community.title())}"]
    tags.append("#ForRent" if prop.is_rent else "#ForSale")
    tags.append("#" + re.sub(r"[^A-Za-z0-9]", "", t_en))
    if prop.is_off_plan:
        tags.append("#OffPlan")
    tags += ["#عقارات_دبي", "#" + ("للإيجار" if prop.is_rent else "للبيع")]
    com_ar = g.community_ar(prop.community, prop.community_ar)
    if com_ar != prop.community:
        tags.append("#" + com_ar.replace(" ", "_"))
    seen: list[str] = []
    for t in tags:
        if t not in seen and len(t) > 1:
            seen.append(t)
    return seen


# --------------------------------------------------------------------------- template writer (mock provider)


def template_listing(prop: Property, keep_en: list[str], keep_ar: list[str]) -> Listing:
    t_en, t_ar = type_words(prop)
    f_en, f_ar = furnishing_words(prop)
    com_ar = g.community_ar(prop.community, prop.community_ar)
    price_en, price_ar = price_phrase(prop)
    deal_en = "for Rent" if prop.is_rent else "for Sale"
    deal_ar = "للإيجار" if prop.is_rent else "للبيع"
    off_en = "Off-Plan " if prop.is_off_plan else ""
    off_ar = " على المخطط" if prop.is_off_plan else ""

    # Titles
    beds_en = g.bedrooms_en(prop.bedrooms)
    if prop.property_type == "studio" or prop.bedrooms == 0:
        head_en = f"{off_en}Studio"
        head_ar = f"استوديو{off_ar}"
    elif beds_en:
        head_en = f"{off_en}{beds_en} {t_en}"
        head_ar = f"{t_ar}{off_ar} من {g.bedrooms_ar(prop.bedrooms, genitive=True)}"
    else:
        head_en, head_ar = f"{off_en}{t_en}", f"{t_ar}{off_ar}"
    where_en = f"{prop.building}, {prop.community}" if prop.building else prop.community
    where_ar = f"{prop.building}، {com_ar}" if prop.building else com_ar
    view_en = prop.view.strip()
    view_ar = g.view_ar(prop.view, prop.view_ar) if prop.view else ""
    title_en = f"{head_en} {deal_en} in {where_en}"
    title_ar = f"{head_ar} {deal_ar} في {where_ar}"
    if view_en and max(len(title_en) + len(view_en), len(title_ar) + len(view_ar)) + 3 <= TITLE_MAX:
        title_en += f" | {view_en.title()}"
        title_ar += f" | {view_ar}"

    # Key facts
    facts_en, facts_ar = [], []
    if prop.bedrooms is not None and prop.bedrooms > 0:
        facts_en.append(f"Bedrooms: {prop.bedrooms}")
        facts_ar.append(f"غرف النوم: {prop.bedrooms}")
    if prop.bathrooms is not None:
        facts_en.append(f"Bathrooms: {prop.bathrooms}")
        facts_ar.append(f"الحمامات: {prop.bathrooms}")
    if prop.size_sqft:
        facts_en.append(f"Built-up area: {fmt_size(prop.size_sqft)} sq ft")
        facts_ar.append(f"المساحة: {fmt_size(prop.size_sqft)} قدم مربع")
    facts_en.append(f"Furnishing: {f_en}")
    facts_ar.append(f"الفرش: {f_ar}")
    if prop.floor:
        facts_en.append(f"Floor: {prop.floor}")
        facts_ar.append(f"الطابق: {prop.floor}")
    if prop.parking:
        facts_en.append(f"Parking: {prop.parking}")
        facts_ar.append(f"المواقف: {g.parking_ar(prop.parking)}")
    if view_en:
        facts_en.append(f"View: {view_en}")
        facts_ar.append(f"الإطلالة: {view_ar}")
    if prop.is_off_plan and prop.handover:
        facts_en.append(f"Expected handover (per developer): {prop.handover}")
        facts_ar.append(f"التسليم المتوقع (حسب المطوّر): {prop.handover}")
    facts_en.append(f"Price: {price_en}")
    facts_ar.append(f"السعر: {price_ar}")

    feats_ar = prop.features_ar or [g.feature_ar(f) for f in prop.features]

    # Intro sentence
    size_en = f" with {fmt_size(prop.size_sqft)} sq ft of built-up area" if prop.size_sqft else ""
    size_ar = f" بمساحة {fmt_size(prop.size_sqft)} قدم مربع" if prop.size_sqft else ""
    status_en = "an off-plan" if prop.is_off_plan else ("a" if not t_en[:1].lower() in "aeiou" else "an")
    f_lower = f_en.lower()
    intro_en = f"{status_en.capitalize()} {f_lower} {head_en.replace('Off-Plan ', '').lower()} {deal_en.lower()} in {where_en}{size_en}."
    intro_en = intro_en.replace(" a a", " a").replace(" studio studio", " studio")
    if prop.property_type == "studio" or prop.bedrooms == 0:
        intro_head_ar = f"استوديو {furnishing_words_masc(prop)}{off_ar}"
    elif prop.bedrooms:
        intro_head_ar = f"{t_ar} {f_ar}{off_ar} من {g.bedrooms_ar(prop.bedrooms, genitive=True)}"
    else:
        intro_head_ar = f"{t_ar} {f_ar}{off_ar}"
    intro_ar = f"{intro_head_ar} {deal_ar} في {where_ar}{size_ar}."
    if view_en:
        intro_en += f" The unit has a {view_en.lower()}."
        intro_ar += f" تتميز الوحدة ب{view_ar}."

    d_en = [intro_en]
    d_ar = [intro_ar]
    if keep_en:
        d_en.append(" ".join(keep_en))
    if keep_ar:
        d_ar.append(" ".join(keep_ar))
    d_en.append("Key facts:\n" + "\n".join(f"- {x}" for x in facts_en))
    d_ar.append("أبرز المعلومات:\n" + "\n".join(f"- {x}" for x in facts_ar))
    if prop.features:
        d_en.append("Features:\n" + "\n".join(f"- {x}" for x in prop.features))
        d_ar.append("المزايا:\n" + "\n".join(f"- {x}" for x in feats_ar))
    if prop.promotions:
        d_en.append("Offer: " + "; ".join(prop.promotions))
        d_ar.append("العرض: " + "؛ ".join(prop.promotions))

    # Social post (short)
    top_en = ", ".join(prop.features[:3])
    top_ar = "، ".join(feats_ar[:3])
    social_en = f"{head_en} {deal_en.lower()} in {prop.community}."
    social_ar = f"{head_ar} {deal_ar} في {com_ar}."
    if prop.size_sqft:
        social_en += f" {fmt_size(prop.size_sqft)} sq ft."
        social_ar += f" {fmt_size(prop.size_sqft)} قدم مربع."
    if top_en:
        social_en += f" {top_en}."
        social_ar += f" {top_ar}."
    social_en += f" {price_en}."
    social_ar += f" {price_ar}."
    if prop.agent_phone:
        social_en += f" Call {prop.agent_phone}."
        social_ar += f" للتواصل: {ltr(prop.agent_phone)}"

    return Listing(
        title_en=title_en,
        title_ar=title_ar,
        description_en="\n\n".join(d_en),
        description_ar="\n\n".join(d_ar),
        social_en=social_en,
        social_ar=social_ar,
        written_by="mock (template writer, no LLM)",
    )


# --------------------------------------------------------------------------- LLM writer

SYSTEM_PROMPT = """You write real estate listings for Dubai property portals and social media, in Modern Standard Arabic and English.

Hard rules:
- Use ONLY the facts in the JSON you receive. Do not add amenities, views, distances, prices, yields, awards or
  anything else that is not in the data.
- No guarantees of any return, rent or price growth; no "risk-free"; no forecasts; no superlatives you cannot
  prove (best, cheapest, No. 1, unbeatable, most luxurious); no pressure wording (hurry, last unit, once in a lifetime).
- Do not invent discounts, waivers or free offers. Mention an offer only if it is in "promotions".
- Off-plan: never say "ready to move in"; give the developer's expected handover only if provided.
- The Arabic is written natively for Gulf readers (Modern Standard Arabic), not a word-for-word translation.
- Do NOT write the permit number, company name, BRN/ORN or escrow details: a compliance footer is appended by code.
- Title: at most 80 characters per language. Description: 120-220 words per language, short paragraphs,
  a "Key facts" list. Social post: at most 280 characters per language, no hashtags (added by code).

Reply with a single JSON object and nothing else:
{"title_en": "...", "title_ar": "...", "description_en": "...", "description_ar": "...", "social_en": "...", "social_ar": "..."}"""


def build_prompt(prop: Property, keep_en: list[str], keep_ar: list[str], feedback: list[Finding] | None = None) -> Prompt:
    t_en, t_ar = type_words(prop)
    f_en, f_ar = furnishing_words(prop)
    price_en, price_ar = price_phrase(prop)
    facts = {
        "purpose": prop.purpose,
        "status": "off-plan" if prop.is_off_plan else "ready",
        "property_type": {"en": t_en, "ar": t_ar},
        "community": {"en": prop.community, "ar": g.community_ar(prop.community, prop.community_ar)},
        "building": prop.building or None,
        "bedrooms": prop.bedrooms,
        "bathrooms": prop.bathrooms,
        "size_sqft": prop.size_sqft,
        "price": {"en": price_en, "ar": price_ar},
        "furnishing": {"en": f_en, "ar": f_ar},
        "view": {"en": prop.view, "ar": g.view_ar(prop.view, prop.view_ar)} if prop.view else None,
        "floor": prop.floor or None,
        "parking_spaces": prop.parking,
        "features": [{"en": e, "ar": a} for e, a in zip(prop.features, prop.features_ar or [g.feature_ar(f) for f in prop.features])],
        "agent_notes_en": keep_en,
        "agent_notes_ar": keep_ar,
        "promotions": prop.promotions,
        "developer": prop.developer or None,
        "project_name": prop.project_name or None,
        "expected_handover": prop.handover or None,
    }
    facts = {k: v for k, v in facts.items() if v not in (None, [], "")}
    user = "Property data (JSON):\n" + json.dumps(facts, ensure_ascii=False, indent=2)
    if feedback:
        user += "\n\nYour previous draft had these problems. Rewrite and fix ALL of them:\n" + "\n".join(
            f"- [{f.code}] {f.where}: {f.message_en}" + (f' (found: "{f.match}")' if f.match else "") for f in feedback
        )
    return Prompt(system=SYSTEM_PROMPT, user=user)


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    m = re.search(r"\{.*\}", t, re.S)
    if not m:
        raise ProviderError("The model did not return JSON")
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ProviderError(f"The model returned invalid JSON: {e}") from e
    missing = [f for f in FIELDS if not isinstance(data.get(f), str) or not data.get(f).strip()]
    if missing:
        raise ProviderError("The model's JSON is missing: " + ", ".join(missing))
    return {f: data[f].strip() for f in FIELDS}


# --------------------------------------------------------------------------- orchestration


def check_listing(listing: Listing, prop: Property) -> list[Finding]:
    """Check each output field. Required particulars are checked on the *published* text = body + footer."""
    out: list[Finding] = []
    for name in FIELDS:
        body = getattr(listing, name)
        lang = name.rsplit("_", 1)[1]
        footer = listing.footer_en if lang == "en" else listing.footer_ar
        is_title = name.startswith("title")
        if is_title:
            out += check_text(body, prop, where=name, require_footer=False)
            if len(body) > TITLE_MAX:
                out.append(
                    Finding(
                        "LW-S03",
                        "info",
                        "style",
                        f"Title is {len(body)} characters (project default limit {TITLE_MAX}).",
                        f"طول العنوان {len(body)} حرفاً (الحد الافتراضي في المشروع {TITLE_MAX}).",
                        where=name,
                        basis="heuristic",
                    )
                )
        else:
            out += check_text(body + "\n\n" + footer, prop, where=name)
    return out


def write_listing(prop: Property, provider=None, max_revisions: int = 1) -> Listing:
    """Generate and check a bilingual listing. ``provider`` is a provider object or a name (default: env / mock)."""
    if provider is None or isinstance(provider, str):
        provider = get_provider(provider)

    input_findings = check_inputs(prop)
    keep_en, drop_en = safe_highlights(prop.highlights)
    keep_ar, drop_ar = safe_highlights(prop.highlights_ar)
    footer_en, footer_ar = compliance_footer(prop)

    if getattr(provider, "is_mock", False):
        listing = template_listing(prop, keep_en, keep_ar)
        listing.footer_en, listing.footer_ar = footer_en, footer_ar
        output_findings = check_listing(listing, prop)
    else:
        feedback: list[Finding] | None = None
        listing = Listing()
        for attempt in range(max_revisions + 1):
            data = parse_json(provider.complete(build_prompt(prop, keep_en, keep_ar, feedback)))
            listing = Listing(**data, written_by=f"{provider.name} ({provider.model})")
            listing.footer_en, listing.footer_ar = footer_en, footer_ar
            output_findings = check_listing(listing, prop)
            listing.revisions = attempt
            errors = [f for f in output_findings if f.severity == "error" and f.category != "compliance"]
            if not errors:
                break
            feedback = errors

    listing.hashtags = hashtags(prop)
    listing.dropped_highlights = drop_en + drop_ar
    listing.sample = prop.sample
    # Data-level compliance findings already explain missing permit/company; drop duplicates from output checks.
    data_codes = {f.code for f in input_findings if f.where == "property"}
    output_findings = [f for f in output_findings if not (f.category == "compliance" and f.code in data_codes)]
    listing.findings = sort_findings(_dedupe(input_findings + output_findings))
    return listing


def _dedupe(findings: list[Finding]) -> list[Finding]:
    seen, out = set(), []
    for f in findings:
        k = (f.code, f.where, f.match)
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def render_text(listing: Listing, lang: str = "both") -> str:
    """Plain-text export: what you paste into a portal or social post."""
    parts = []
    if lang in ("en", "both"):
        parts += [listing.title_en, "", listing.description_en, "", listing.footer_en, "", "Social:", listing.social_en, " ".join(listing.hashtags)]
    if lang in ("ar", "both"):
        if parts:
            parts += ["", "-" * 40, ""]
        parts += [listing.title_ar, "", listing.description_ar, "", listing.footer_ar, "", "منشور التواصل الاجتماعي:", listing.social_ar, " ".join(listing.hashtags)]
    return "\n".join(parts).strip() + "\n"
