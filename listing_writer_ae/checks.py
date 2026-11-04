"""Deterministic checks for Dubai property ads (Arabic and English).

Four categories:

* ``compliance``  - advertising requirements published by Dubai Land Department (DLD) / RERA:
                    permit number, company name, off-plan particulars, promotional campaign permit, QR code.
                    Each finding cites an official source from ``sources.py``.
* ``claim``       - exaggerated, unverifiable or risky marketing claims ("guaranteed ROI", "best price",
                    "risk-free", "prices will double", ...). The DLD basis is the general duty that the
                    advertiser is responsible for the validity and credibility of the content; the phrase
                    lists themselves are this project's heuristics (``basis = "heuristic"``).
* ``consistency`` - the text says something the property data does not (3 bedrooms vs 2, a private pool
                    that is not in the features, "ready to move in" for an off-plan unit, a different price).
* ``style``       - readability issues portals and readers dislike (SHOUTING, "!!!").

The checker never calls an LLM. It is not legal advice: it cannot see the permit itself, cannot tell whether
a claim is true, and the rules may have changed since ``sources.CHECKED``.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .arabic import normalise, normalise_with_map, to_ascii_digits
from .schema import Property

SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Finding:
    code: str
    severity: str  # error | warning | info
    category: str  # compliance | claim | consistency | style
    message_en: str
    message_ar: str
    where: str = ""  # e.g. "description_ar", "input:highlights", "property"
    match: str = ""
    suggestion_en: str = ""
    suggestion_ar: str = ""
    sources: list[str] = field(default_factory=list)
    basis: str = "official"  # official | heuristic | data

    def to_dict(self) -> dict:
        return asdict(self)


def _placeholder(value: str) -> bool:
    v = value.strip().lower()
    return not v or v in {"tbd", "tba", "n/a", "na", "none", "-", "pending", "xxx", "0", "000", "todo"} or set(v) <= {"x", "0", "-"}


# --------------------------------------------------------------------------- property-level compliance


def check_property(prop: Property) -> list[Finding]:
    """Compliance checks on the data itself (before any text is written)."""
    out: list[Finding] = []
    if _placeholder(prop.permit_number):
        out.append(
            Finding(
                "LW-P01",
                "error",
                "compliance",
                "No advertising permit number. Dubai property ads need a RERA permit obtained through Trakheesi, "
                "and the permit number must be displayed on the ad.",
                "لا يوجد رقم تصريح إعلان. الإعلانات العقارية في دبي تحتاج تصريحاً من مؤسسة التنظيم العقاري عبر نظام "
                "«تراخيصي»، ويجب إظهار رقم التصريح في الإعلان.",
                where="property",
                suggestion_en="Apply for the ad permit in Trakheesi, then add permit_number.",
                suggestion_ar="اطلب تصريح الإعلان عبر «تراخيصي» ثم أضف رقم التصريح.",
                sources=["rera-circular-2-2022", "dld-2020-permits", "dld-brokerage-guide-2024"],
            )
        )
    if not prop.company_name:
        out.append(
            Finding(
                "LW-P03",
                "error",
                "compliance",
                "No company name. Written and visual ads must include the name of the real estate company.",
                "لا يوجد اسم الشركة. يجب أن يتضمن الإعلان المكتوب أو المرئي اسم الشركة العقارية.",
                where="property",
                suggestion_en="Set company_name to the licensed brokerage's name.",
                suggestion_ar="أضف اسم شركة الوساطة المرخّصة.",
                sources=["rera-circular-2-2022"],
            )
        )
    if prop.is_off_plan:
        required = [
            ("developer", "developer name", "اسم المطوّر"),
            ("project_name", "project name", "اسم المشروع"),
            ("project_number", "project number", "رقم المشروع"),
            ("project_location", "project location", "موقع المشروع"),
            ("escrow_account", "escrow account number", "رقم حساب الضمان"),
        ]
        missing = [(en, ar) for name, en, ar in required if _placeholder(getattr(prop, name))]
        if missing:
            out.append(
                Finding(
                    "LW-P04",
                    "error",
                    "compliance",
                    "Off-plan ad is missing: " + ", ".join(en for en, _ in missing) + ".",
                    "إعلان على المخطط ينقصه: " + "، ".join(ar for _, ar in missing) + ".",
                    where="property",
                    suggestion_en="Off-plan ads must show developer, project name, project number, location and escrow account.",
                    suggestion_ar="إعلانات البيع على المخطط يجب أن تذكر المطوّر واسم المشروع ورقمه وموقعه ورقم حساب الضمان.",
                    sources=["rera-circular-2-2022"],
                )
            )
    if prop.promotions and _placeholder(prop.promo_permit_number):
        out.append(
            Finding(
                "LW-P05",
                "error",
                "compliance",
                "The ad includes a promotion (" + "; ".join(prop.promotions) + ") but no promotional campaign permit.",
                "الإعلان يتضمن عرضاً ترويجياً (" + "؛ ".join(prop.promotions) + ") دون تصريح حملة ترويجية.",
                where="property",
                suggestion_en="Get a promotional campaign permit, or remove the promotion from the ad.",
                suggestion_ar="احصل على تصريح حملة ترويجية، أو احذف العرض من الإعلان.",
                sources=["rera-circular-2-2022"],
            )
        )
    if not prop.qr_code_ready:
        out.append(
            Finding(
                "LW-P06",
                "warning",
                "compliance",
                "QR code not confirmed. DLD requires the ad to carry the permit's QR code, readable when scanned, "
                "and the ad data must match it.",
                "رمز QR غير مؤكَّد. تشترط الدائرة أن يحمل الإعلان رمز QR الخاص بالتصريح، وأن يكون مقروءاً عند المسح، "
                "وأن تطابق بيانات الإعلان ما فيه.",
                where="property",
                suggestion_en="Attach the DLD-issued QR code to the listing image or portal listing, then set qr_code_ready.",
                suggestion_ar="أرفق رمز QR الصادر من الدائرة بصورة الإعلان أو بالبوابة، ثم فعّل qr_code_ready.",
                sources=["dld-2024-qr", "dld-2024-256-brokers"],
            )
        )
    return out


# --------------------------------------------------------------------------- claim rules

_SUGGEST_FACT_EN = "State the verifiable fact instead (e.g. the actual price, size or recent rent), or remove it."
_SUGGEST_FACT_AR = "اذكر الحقيقة القابلة للتحقق بدلاً من ذلك (السعر الفعلي أو المساحة أو الإيجار الحالي)، أو احذف العبارة."


@dataclass
class _Rule:
    code: str
    severity: str
    message_en: str
    message_ar: str
    en: list[str]
    ar: list[str]
    suggestion_en: str = _SUGGEST_FACT_EN
    suggestion_ar: str = _SUGGEST_FACT_AR
    sources: list[str] = field(default_factory=lambda: ["rera-circular-2-2022"])
    category: str = "claim"
    basis: str = "heuristic"


# English patterns are matched case-insensitively on the raw text; Arabic patterns are normalised with
# the same function as the text (alef forms, ta marbuta, diacritics), so write them in plain spelling.
CLAIM_RULES: list[_Rule] = [
    _Rule(
        "LW-C01",
        "error",
        "Guaranteed return / ROI / rental income. Returns depend on the market and the tenant and cannot be "
        "guaranteed by an ad.",
        "عائد أو دخل إيجاري «مضمون». العوائد تعتمد على السوق والمستأجر ولا يمكن لإعلان أن يضمنها.",
        en=[
            r"\bguarantee[ds]?\b[^.\n]{0,30}\b(roi|returns?|yields?|income|rental|rent|profits?|appreciation)\b",
            r"\b(roi|returns?|yields?|income|profits?)\b[^.\n]{0,20}\bguarantee[ds]?\b",
            r"\bassured\s+(roi|returns?|yields?|income|rental)\b",
        ],
        ar=[
            r"(عائد|عوائد|دخل|ربح|ارباح|عايد)\s*(ايجاري\s*)?(مضمون|مضمونه|مؤكد|مؤكده)",
            r"ضمان\s*(العائد|الدخل|الربح|الارباح)",
            r"(عائد|عايد)\s*(سنوي\s*)?(ثابت|مضمون)",
        ],
        suggestion_en="Remove the guarantee. If you cite a yield, say how it was calculated and that it is not guaranteed.",
        suggestion_ar="احذف كلمة «مضمون». إن ذكرت عائداً فاشرح طريقة حسابه وأنه غير مضمون.",
    ),
    _Rule(
        "LW-C02",
        "warning",
        "Unverifiable superlative (best / cheapest / No. 1 / unbeatable).",
        "صيغة تفضيل لا يمكن إثباتها (الأفضل / الأرخص / رقم 1 / لا مثيل له).",
        en=[
            r"\b(the\s+)?best\s+(price|deal|value|offer|investment|unit|location|view)s?\b",
            r"\bcheapest\b",
            r"\blowest\s+price\b",
            r"\b(no\.?\s*1|number\s+one|#\s?1)\b",
            r"\bunbeatable\b",
            r"\bunmatched\b",
            r"\bsecond\s+to\s+none\b",
            r"\bmost\s+(luxurious|prestigious|exclusive)\b",
        ],
        ar=[
            r"افضل\s+(سعر|صفقه|عرض|استثمار|موقع|قيمه|اطلاله)",
            r"\bالافضل\b",
            r"\bارخص\b",
            r"\bالارخص\b",
            r"اقل\s+سعر",
            r"رقم\s*(1|واحد)\b",
            r"لا\s+مثيل\s+له",
            r"لا\s+يضاهي",
            r"لا\s+يعلي\s+عليه",
            r"\bالافخم\b",
        ],
    ),
    _Rule(
        "LW-C03",
        "error",
        "Risk-free / certain-profit claim. Property investment carries risk.",
        "ادعاء «بدون مخاطر» أو «ربح أكيد». الاستثمار العقاري ينطوي على مخاطر.",
        en=[
            r"\brisk[\s-]?free\b",
            r"\b(no|zero)\s+risks?\b",
            r"\b100\s?%\s+(safe|secure|guaranteed)\b",
            r"\b(sure|certain)\s+profits?\b",
            r"\bcan'?t\s+lose\b",
        ],
        ar=[r"(بدون|بلا|من\s+غير|دون)\s+(اي\s+)?مخاطر", r"مضمون\s*100", r"100\s*%?\s*مضمون", r"(ربح|ارباح)\s+(اكيد|اكيده|مؤكد)"],
        suggestion_en="Remove the risk claim.",
        suggestion_ar="احذف ادعاء انعدام المخاطر.",
    ),
    _Rule(
        "LW-C04",
        "error",
        "Forecast of future price or capital appreciation stated as fact.",
        "توقّع لارتفاع الأسعار أو قيمة العقار مذكور وكأنه حقيقة.",
        en=[
            r"\b(price|value|prices|values)\s+(will|is\s+going\s+to|are\s+going\s+to)\s+(double|rise|increase|go\s+up|skyrocket)",
            r"\bwill\s+(double|triple)\b",
            r"\bguaranteed\s+(capital\s+)?(growth|appreciation)\b",
        ],
        ar=[r"(سيتضاعف|ستتضاعف|سيرتفع|سترتفع|ستزيد|سيزيد)\s+(سعر|السعر|الاسعار|قيمه|القيمه)", r"(الاسعار|السعر|القيمه)\s+(سترتفع|سيرتفع|ستتضاعف|سيتضاعف)"],
        suggestion_en="Remove the forecast, or cite published historical data with its source and date.",
        suggestion_ar="احذف التوقّع، أو استشهد ببيانات تاريخية منشورة مع مصدرها وتاريخها.",
    ),
    _Rule(
        "LW-C05",
        "warning",
        "Scarcity or pressure wording (last unit, once in a lifetime, hurry). Only use it if it is literally true.",
        "عبارات ضغط أو ندرة (آخر وحدة، فرصة لا تتكرر، سارع). استخدمها فقط إن كانت صحيحة حرفياً.",
        en=[
            r"\b(last|only)\s+(one|unit|few\s+units?)\s*(left|remaining|available)?\b",
            r"\bonce[\s-]in[\s-]a[\s-]lifetime\b",
            r"\bhurry\b",
            r"\bact\s+(now|fast)\b",
            r"\bdon'?t\s+miss\s+out\b",
            r"\bwon'?t\s+last\b",
        ],
        ar=[r"اخر\s+وحده", r"فرصه\s+(لا|لن)\s+(تتكرر|تعوض)", r"\bسارع", r"لا\s+تفوت", r"الفرصه\s+الاخيره"],
        suggestion_en="Replace with a factual availability statement, or remove it.",
        suggestion_ar="استبدلها بمعلومة واقعية عن التوفّر، أو احذفها.",
    ),
    _Rule(
        "LW-C06",
        "warning",
        "'Below market price' claim. Back it with comparable DLD transactions or remove it.",
        "ادعاء «أقل من سعر السوق». ادعمه بصفقات مماثلة مسجلة لدى الدائرة أو احذفه.",
        en=[r"\bbelow\s+(the\s+)?market\s+(price|value|rate)?", r"\bunder\s+market\s+value\b", r"\bbelow\s+original\s+price\b"],
        ar=[r"اقل\s+من\s+(سعر|اسعار|قيمه)\s+السوق", r"تحت\s+سعر\s+السوق"],
    ),
    _Rule(
        "LW-C07",
        "info",
        "Golden Visa mentioned. Eligibility is decided by the authorities on their current criteria; do not promise it.",
        "ذُكرت «الإقامة الذهبية». الأهلية تحددها الجهات المختصة وفق معاييرها الحالية؛ لا تَعِد بها في الإعلان.",
        en=[r"\bgolden\s+visa\b"],
        ar=[r"(الاقامه|التاشيره|الفيزا)\s+الذهبيه"],
        suggestion_en="Prefer 'may be eligible, subject to official criteria' over 'comes with a Golden Visa'.",
        suggestion_ar="الأفضل: «قد يكون مؤهلاً وفق المعايير الرسمية» بدلاً من «يمنحك الإقامة الذهبية».",
        sources=[],
    ),
    _Rule(
        "LW-C08",
        "info",
        "Travel-time claim (\"5 minutes from ...\"). Make sure it is realistic and say how (by car, walking).",
        "ادعاء عن مدة الوصول («5 دقائق من ...»). تأكد أنه واقعي واذكر الوسيلة (بالسيارة، سيراً).",
        en=[r"\b\d+\s*(min|mins|minutes?)\s+(from|to|away)\b", r"\bminutes\s+(from|to|away)\b"],
        ar=[r"\d+\s*(دقيقه|دقايق|دقائق)\s+(من|عن|الي)", r"دقائق\s+(من|عن)"],
        suggestion_en="Write e.g. 'approx. 10 minutes by car to ...'.",
        suggestion_ar="اكتب مثلاً: «نحو 10 دقائق بالسيارة إلى ...».",
        sources=[],
    ),
    _Rule(
        "LW-C09",
        "warning",
        "'Sold' wording. A reported DLD circular allows 'sold' ads only after the transfer is registered.",
        "عبارة «تم البيع». بحسب تعميم منقول عن الدائرة، لا يُنشر إعلان «تم البيع» إلا بعد تسجيل نقل الملكية.",
        en=[r"\bjust\s+sold\b", r"\bsold\s+out\b", r"\brecently\s+sold\b"],
        ar=[r"تم\s+البيع", r"بيعت\s+بالكامل", r"نفدت\s+الوحدات"],
        suggestion_en="Only publish after the transfer to the buyer is registered.",
        suggestion_ar="لا تنشره إلا بعد تسجيل نقل الملكية للمشتري.",
        sources=["gulfnews-2024-just-sold"],
    ),
]

# Words that make an ad a "promotional campaign" in the sense of RERA Circular 2-2022 item 5.
PROMO_EN = [
    r"(?<!chiller )(?<!chiller-)(?<!duty )(?<!duty-)(?<!risk )(?<!risk-)(?<!toll )(?<!tax )(?<!hands )\bfree\b(?![\s-]*hold)(?![\s-]*zone)",
    r"\bwaiver\b",
    r"\bwaived\b",
    r"\bdiscount(ed|s)?\b",
    r"\b\d+\s?%\s+off\b",
    r"\bcash\s?back\b",
    r"\bno\s+(dld|registration|agency|commission)\s+fees?\b",
]
PROMO_AR = [r"\bمجانا\b", r"(?<!تبريد )\bمجاني(ه)?\b", r"\bخصم\b", r"\bاعفاء\b", r"استرداد\s+نقدي", r"بدون\s+(رسوم|عموله)"]


def _compile_en(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def _compile_ar(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(normalise(p)) for p in patterns]


_COMPILED = [(r, _compile_en(r.en), _compile_ar(r.ar)) for r in CLAIM_RULES]
_PROMO = (_compile_en(PROMO_EN), _compile_ar(PROMO_AR))


def _first_match(text: str, norm: str, en: list[re.Pattern], ar: list[re.Pattern]) -> str | None:
    for p in en:
        m = p.search(text)
        if m:
            return m.group(0)
    if not ar:
        return None
    norm_m, idx = normalise_with_map(text)
    for p in ar:
        m = p.search(norm_m)
        if m and m.end() > m.start():
            # map the normalised span back to the original text for display
            return text[idx[m.start()] : idx[m.end() - 1] + 1]
    return None


def check_claims(text: str, where: str = "text") -> list[Finding]:
    out: list[Finding] = []
    norm = normalise(text)
    for rule, en, ar in _COMPILED:
        m = _first_match(text, norm, en, ar)
        if m:
            out.append(
                Finding(
                    rule.code,
                    rule.severity,
                    rule.category,
                    rule.message_en,
                    rule.message_ar,
                    where=where,
                    match=m.strip(),
                    suggestion_en=rule.suggestion_en,
                    suggestion_ar=rule.suggestion_ar,
                    sources=list(rule.sources),
                    basis=rule.basis,
                )
            )
    return out


def mentions_promotion(text: str) -> str | None:
    return _first_match(text, normalise(text), *_PROMO)


# --------------------------------------------------------------------------- consistency with data

# (english regexes, arabic regexes, predicate(prop) -> True if the data supports the claim, label en, label ar)
_FEATURE_CLAIMS = [
    ([r"\bprivate\s+pool\b"], [r"مسبح\s+خاص", r"حمام\s+سباحه\s+خاص"], "private pool", "مسبح خاص"),
    ([r"\bprivate\s+beach\b", r"\bbeach\s+access\b"], [r"شاطئ\s+خاص", r"وصول\s+(مباشر\s+)?(الي|إلى)\s+الشاطئ"], "beach access", "الوصول إلى الشاطئ"),
    ([r"\bmaid'?s?\s+room\b"], [r"غرفه\s+(خادمه|الخادمه)"], "maid's room", "غرفة خادمة"),
    ([r"\bprivate\s+garden\b"], [r"حديقه\s+خاصه"], "private garden", "حديقة خاصة"),
    ([r"\bsea\s+views?\b", r"\bocean\s+views?\b"], [r"اطلاله\s+(علي|على)\s+البحر"], "sea view", "إطلالة على البحر"),
    ([r"\bburj\s+khalifa\s+views?\b"], [r"اطلاله\s+(علي|على)\s+برج\s+خليفه"], "burj khalifa view", "إطلالة على برج خليفة"),
    ([r"\bchiller[\s-]free\b"], [r"تبريد\s+مجاني"], "chiller free", "تبريد مجاني"),
    ([r"\bpenthouse\b"], [r"بنتهاوس"], "penthouse", "بنتهاوس"),
]
_COMPILED_FEATURES = [(_compile_en(e), _compile_ar(a), en, ar) for e, a, en, ar in _FEATURE_CLAIMS]


def _data_blob(prop: Property) -> str:
    parts = [prop.view, prop.view_ar, prop.highlights, prop.highlights_ar, prop.property_type.replace("_", " "), prop.furnishing]
    parts += prop.features + prop.features_ar
    return normalise(" ".join(parts))


def _data_supports(prop: Property, label_en: str, en: list[re.Pattern], ar: list[re.Pattern]) -> bool:
    blob = _data_blob(prop)
    raw = " ".join([prop.view, prop.highlights, prop.property_type.replace("_", " ")] + prop.features)
    if label_en in blob:
        return True
    return any(p.search(raw) for p in en) or any(p.search(blob) for p in ar)


_NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
_PRICE_EN = re.compile(r"(?:AED|Dhs?\.?|Dirhams?)\s*" + _NUM + r"\s*(k|m|mn|million)?\b|" + _NUM + r"\s*(k|m|mn|million)?\s*(?:AED|Dhs?\b|dirhams?)", re.IGNORECASE)
_PRICE_AR = re.compile(_NUM + r"\s*(الف|مليون)?\s*(درهم|د\.ا|د\.إ)")
_SIZE = re.compile(_NUM + r"\s*(?:sq\.?\s*ft|sqft|sq\s+feet|square\s+feet|قدم\s+مربع|قدما\s+مربعا|قدم²)", re.IGNORECASE)
_BEDS_EN = re.compile(r"\b(\d+)\s*(?:-|\s)?\s*(?:bed(?:room)?s?|br|bhk)\b", re.IGNORECASE)
_BEDS_AR = re.compile(r"(\d+)\s+غرف\s+نوم")


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def _scale(v: float, unit: str | None) -> float:
    u = (unit or "").lower()
    if u == "k" or u == "الف":
        return v * 1_000
    if u in {"m", "mn", "million", "مليون"}:
        return v * 1_000_000
    return v


def _allowed_prices(prop: Property) -> list[float]:
    p = prop.price_aed or 0
    allowed = [p]
    if prop.is_rent:
        if prop.rent_period == "yearly":
            allowed.append(p / 12)
            if prop.cheques:
                allowed.append(p / prop.cheques)
        else:
            allowed.append(p * 12)
    return allowed


def _close(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(a - b) <= max(1.0, abs(b) * tol)


def check_consistency(text: str, prop: Property, where: str = "text") -> list[Finding]:
    out: list[Finding] = []
    t = to_ascii_digits(text)
    norm = normalise(text)

    # bedrooms
    if prop.bedrooms is not None:
        said = {int(m.group(1)) for m in _BEDS_EN.finditer(t)} | {int(m.group(1)) for m in _BEDS_AR.finditer(t)}
        if re.search(normalise("غرفتا نوم|غرفتين نوم|غرفتي نوم"), norm):
            said.add(2)
        if re.search(normalise("غرفة نوم واحدة"), norm):
            said.add(1)
        wrong = sorted(n for n in said if n != prop.bedrooms)
        if wrong:
            out.append(
                Finding(
                    "LW-D01",
                    "error",
                    "consistency",
                    f"Text mentions {wrong[0]} bedroom(s) but the property data says {prop.bedrooms}.",
                    f"عدد غرف النوم في النص ({wrong[0]}) يخالف بيانات العقار ({prop.bedrooms}).",
                    where=where,
                    match=str(wrong[0]),
                    suggestion_en="Fix the text or the data so they agree.",
                    suggestion_ar="صحّح النص أو البيانات لتتطابق.",
                    sources=["rera-circular-2-2022", "dld-2024-256-brokers"],
                    basis="data",
                )
            )

    # size
    if prop.size_sqft:
        for m in _SIZE.finditer(t):
            v = _num(m.group(1))
            if not _close(v, prop.size_sqft):
                out.append(
                    Finding(
                        "LW-D02",
                        "error",
                        "consistency",
                        f"Text says {m.group(0).strip()} but the property data says {prop.size_sqft:,.0f} sq ft.",
                        f"النص يذكر {m.group(0).strip()} بينما بيانات العقار تقول {prop.size_sqft:,.0f} قدم مربع.",
                        where=where,
                        match=m.group(0).strip(),
                        suggestion_en="Use the size from the title deed / Oqood / Ejari.",
                        suggestion_ar="استخدم المساحة المذكورة في سند الملكية أو «عقود» أو «إيجاري».",
                        sources=["rera-circular-2-2022", "dld-2024-256-brokers"],
                        basis="data",
                    )
                )
                break

    # price
    if prop.price_aed:
        allowed = _allowed_prices(prop)
        hits = []
        for m in _PRICE_EN.finditer(t):
            num, unit = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
            hits.append((m.group(0).strip(), _scale(_num(num), unit)))
        for m in _PRICE_AR.finditer(t):
            hits.append((m.group(0).strip(), _scale(_num(m.group(1)), m.group(2) and normalise(m.group(2)))))
        for raw, v in hits:
            if not any(_close(v, a) for a in allowed):
                out.append(
                    Finding(
                        "LW-D03",
                        "error",
                        "consistency",
                        f"Price in text ({raw}) differs from the property data (AED {prop.price_aed:,.0f}).",
                        f"السعر في النص ({raw}) يختلف عن بيانات العقار ({prop.price_aed:,.0f} درهم).",
                        where=where,
                        match=raw,
                        suggestion_en="The advertised price must match the permit and the data.",
                        suggestion_ar="يجب أن يطابق السعر المعلن التصريح والبيانات.",
                        sources=["rera-circular-2-2022", "dld-2024-256-brokers"],
                        basis="data",
                    )
                )
                break

    # status
    ready_en = re.search(r"\b(ready\s+to\s+move|move[\s-]in\s+ready|ready\s+for\s+occupancy|vacant\s+now)\b", t, re.I)
    ready_ar = re.search(normalise(r"جاهز(ة)?\s+(لل)?سكن|جاهز(ة)?\s+للانتقال|جاهز(ة)?\s+للاستلام\s+فورا"), norm)
    off_en = re.search(r"\boff[\s-]plan\b", t, re.I)
    off_ar = re.search(normalise("على المخطط"), norm)
    if prop.is_off_plan and (ready_en or ready_ar):
        m = (ready_en or ready_ar).group(0)
        out.append(
            Finding(
                "LW-D04",
                "error",
                "consistency",
                "Text says the unit is ready to move in, but the data says off-plan.",
                "النص يقول إن الوحدة جاهزة للسكن، بينما البيانات تقول إنها على المخطط.",
                where=where,
                match=m,
                suggestion_en="State the developer's expected handover date instead.",
                suggestion_ar="اذكر موعد التسليم المتوقع حسب المطوّر بدلاً من ذلك.",
                sources=["rera-circular-2-2022"],
                basis="data",
            )
        )
    if not prop.is_off_plan and (off_en or off_ar):
        m = (off_en or off_ar).group(0)
        out.append(
            Finding(
                "LW-D04",
                "error",
                "consistency",
                "Text says off-plan, but the data says the unit is ready.",
                "النص يقول «على المخطط» بينما البيانات تقول إن الوحدة جاهزة.",
                where=where,
                match=m,
                sources=["rera-circular-2-2022"],
                basis="data",
            )
        )

    # furnishing
    furnished_en = re.search(r"(?<!un)(?<!partly )(?<!partially )\b(fully\s+)?furnished\b", t, re.I)
    furnished_ar = re.search(normalise(r"(?<!غير )\bمفروش(ة)?\b(?!\s+جزئيا)"), norm)
    if prop.furnishing == "unfurnished" and (furnished_en or furnished_ar):
        m = (furnished_en or furnished_ar).group(0)
        out.append(
            Finding(
                "LW-D05",
                "error",
                "consistency",
                "Text says furnished, but the data says unfurnished.",
                "النص يقول «مفروشة» بينما البيانات تقول «غير مفروشة».",
                where=where,
                match=m,
                sources=["rera-circular-2-2022"],
                basis="data",
            )
        )

    # amenities / views claimed but absent from the data
    for en, ar, label_en, label_ar in _COMPILED_FEATURES:
        hit = _first_match(text, norm, en, ar)
        if hit and not _data_supports(prop, label_en, en, ar):
            out.append(
                Finding(
                    "LW-D06",
                    "warning",
                    "consistency",
                    f"Text claims '{label_en}', which is not in the property data.",
                    f"النص يذكر «{label_ar}» وهي غير موجودة في بيانات العقار.",
                    where=where,
                    match=hit,
                    suggestion_en="Add it to the data if true, otherwise remove it from the text.",
                    suggestion_ar="أضفها إلى البيانات إن كانت صحيحة، وإلا فاحذفها من النص.",
                    sources=["rera-circular-2-2022"],
                    basis="data",
                )
            )
    return out


# --------------------------------------------------------------------------- style


def check_style(text: str, where: str = "text") -> list[Finding]:
    out: list[Finding] = []
    words = re.findall(r"\b[A-Za-z]{3,}\b", text)
    caps = [w for w in words if w.isupper() and w not in {"AED", "DLD", "RERA", "BRN", "ORN", "JBR", "JLT", "JVC", "DIFC", "SQFT", "ROI"}]
    if len(words) >= 8 and len(caps) / len(words) > 0.3:
        out.append(
            Finding(
                "LW-S01",
                "info",
                "style",
                "Too much text in CAPITALS; it reads as shouting and some portals reject it.",
                "نص كثير بالأحرف الكبيرة؛ يبدو كالصراخ وقد ترفضه بعض البوابات.",
                where=where,
                match=" ".join(caps[:4]),
                basis="heuristic",
            )
        )
    m = re.search(r"[!！]{2,}", text)
    if m or text.count("!") > 3:
        out.append(
            Finding(
                "LW-S02",
                "info",
                "style",
                "Too many exclamation marks.",
                "علامات تعجب كثيرة.",
                where=where,
                match=m.group(0) if m else "!",
                basis="heuristic",
            )
        )
    return out


# --------------------------------------------------------------------------- ad-text compliance


def _contains_token(text: str, token: str) -> bool:
    if not token:
        return True
    a = re.sub(r"[\s\-]", "", to_ascii_digits(text)).lower()
    b = re.sub(r"[\s\-]", "", to_ascii_digits(token)).lower()
    return b in a


def check_ad_text(text: str, prop: Property, where: str = "text") -> list[Finding]:
    """Does the published text itself carry what the circular requires?"""
    out: list[Finding] = []
    if not _placeholder(prop.permit_number) and not _contains_token(text, prop.permit_number):
        out.append(
            Finding(
                "LW-P02",
                "error",
                "compliance",
                f"The permit number ({prop.permit_number}) does not appear in this text.",
                f"رقم التصريح ({prop.permit_number}) غير موجود في هذا النص.",
                where=where,
                suggestion_en="Add 'Permit No.: ...' to the ad.",
                suggestion_ar="أضف «رقم التصريح: ...» إلى الإعلان.",
                sources=["rera-circular-2-2022", "dld-2020-permits"],
            )
        )
    if prop.company_name and not _contains_token(text, prop.company_name):
        out.append(
            Finding(
                "LW-P03",
                "error",
                "compliance",
                f"The company name ({prop.company_name}) does not appear in this text.",
                f"اسم الشركة ({prop.company_name}) غير موجود في هذا النص.",
                where=where,
                sources=["rera-circular-2-2022"],
            )
        )
    if prop.is_off_plan:
        missing = [
            label
            for label, val in (
                ("developer", prop.developer),
                ("project name", prop.project_name),
                ("project number", prop.project_number),
                ("escrow account", prop.escrow_account),
            )
            if not _placeholder(val) and not _contains_token(text, val)
        ]
        if missing:
            out.append(
                Finding(
                    "LW-P04",
                    "error",
                    "compliance",
                    "Off-plan particulars missing from this text: " + ", ".join(missing) + ".",
                    "بيانات البيع على المخطط غير موجودة في هذا النص: " + "، ".join(missing) + ".",
                    where=where,
                    sources=["rera-circular-2-2022"],
                )
            )
    promo = mentions_promotion(text)
    if promo and _placeholder(prop.promo_permit_number) and not prop.promotions:
        out.append(
            Finding(
                "LW-P05",
                "error",
                "compliance",
                f"The text advertises a promotion ('{promo.strip()}') but there is no promotional campaign permit.",
                f"النص يعلن عن عرض ترويجي («{promo.strip()}») دون تصريح حملة ترويجية.",
                where=where,
                match=promo.strip(),
                suggestion_en="Get a promotional campaign permit, or remove the offer.",
                suggestion_ar="احصل على تصريح حملة ترويجية، أو احذف العرض.",
                sources=["rera-circular-2-2022"],
            )
        )
    return out


# --------------------------------------------------------------------------- entry points


def check_text(text: str, prop: Property | None = None, where: str = "text", require_footer: bool = True) -> list[Finding]:
    """Check one piece of ad text. With ``prop`` it also checks consistency and required particulars."""
    out = check_claims(text, where) + check_style(text, where)
    if prop is not None:
        out += check_consistency(text, prop, where)
        if require_footer:
            out += check_ad_text(text, prop, where)
    elif mentions_promotion(text):
        m = mentions_promotion(text) or ""
        out.append(
            Finding(
                "LW-P05",
                "warning",
                "compliance",
                f"The text advertises a promotion ('{m.strip()}'). Promotional campaigns need their own permit.",
                f"النص يعلن عن عرض ترويجي («{m.strip()}»). الحملات الترويجية تحتاج تصريحاً خاصاً.",
                where=where,
                match=m.strip(),
                sources=["rera-circular-2-2022"],
            )
        )
    return sort_findings(out)


def check_inputs(prop: Property) -> list[Finding]:
    """Data-level compliance plus claim checks on the agent's free-text highlights (input side)."""
    out = check_property(prop)
    if prop.highlights:
        out += check_claims(prop.highlights, "input:highlights")
    if prop.highlights_ar:
        out += check_claims(prop.highlights_ar, "input:highlights_ar")
    for i, p in enumerate(prop.promotions):
        out += check_claims(p, f"input:promotions[{i}]")
    return sort_findings(out)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.code, f.where))


def summarise(findings: list[Finding]) -> dict[str, int]:
    s = {"error": 0, "warning": 0, "info": 0}
    for f in findings:
        s[f.severity] = s.get(f.severity, 0) + 1
    return s
