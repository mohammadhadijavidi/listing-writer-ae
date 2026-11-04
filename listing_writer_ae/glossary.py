"""Arabic/English vocabulary for Dubai listings: property types, communities, common features.

The Arabic community names are the forms commonly used in Arabic-language Dubai property marketing.
Anything not found here is passed through unchanged (or uses the `*_ar` override from the input),
so the template writer never invents a translation.
"""

from __future__ import annotations

PROPERTY_TYPE = {
    "apartment": ("Apartment", "شقة"),
    "studio": ("Studio", "استوديو"),
    "villa": ("Villa", "فيلا"),
    "townhouse": ("Townhouse", "تاون هاوس"),
    "penthouse": ("Penthouse", "بنتهاوس"),
    "duplex": ("Duplex", "دوبلكس"),
    "hotel_apartment": ("Hotel Apartment", "شقة فندقية"),
    "office": ("Office", "مكتب"),
    "retail": ("Retail Unit", "محل تجاري"),
    "warehouse": ("Warehouse", "مستودع"),
    "land": ("Plot", "أرض"),
}

# Gender of the Arabic noun, used to agree adjectives ("مفروشة" vs "مفروش").
FEMININE_TYPES = {"apartment", "villa", "hotel_apartment", "land"}

COMMUNITY_AR = {
    "dubai marina": "دبي مارينا",
    "downtown dubai": "وسط مدينة دبي",
    "business bay": "الخليج التجاري",
    "palm jumeirah": "نخلة جميرا",
    "jumeirah village circle": "قرية جميرا الدائرية",
    "jvc": "قرية جميرا الدائرية",
    "jumeirah lake towers": "أبراج بحيرات جميرا",
    "jlt": "أبراج بحيرات جميرا",
    "jumeirah beach residence": "جميرا بيتش ريزيدنس",
    "jbr": "جميرا بيتش ريزيدنس",
    "dubai hills estate": "دبي هيلز استيت",
    "arabian ranches": "المرابع العربية",
    "dubai creek harbour": "دبي كريك هاربر",
    "al barsha": "البرشاء",
    "deira": "ديرة",
    "bur dubai": "بر دبي",
    "al furjan": "الفرجان",
    "mirdif": "مردف",
    "dubai silicon oasis": "واحة دبي للسيليكون",
    "international city": "المدينة العالمية",
    "dubai south": "دبي الجنوب",
    "meydan": "ميدان",
    "city walk": "سيتي ووك",
    "emirates hills": "تلال الإمارات",
    "the springs": "الينابيع",
    "the meadows": "المروج",
    "the greens": "الروضة",
    "al quoz": "القوز",
    "jumeirah": "جميرا",
    "umm suqeim": "أم سقيم",
    "difc": "مركز دبي المالي العالمي",
    "damac hills": "داماك هيلز",
    "town square": "تاون سكوير",
    "motor city": "موتور سيتي",
    "sports city": "مدينة دبي الرياضية",
    "dubai sports city": "مدينة دبي الرياضية",
    "al jaddaf": "الجداف",
    "sobha hartland": "صبحا هارتلاند",
    "mohammed bin rashid city": "مدينة محمد بن راشد",
}

FURNISHING = {
    "furnished": ("Furnished", "مفروشة", "مفروش"),
    "unfurnished": ("Unfurnished", "غير مفروشة", "غير مفروش"),
    "partly_furnished": ("Partly furnished", "مفروشة جزئياً", "مفروش جزئياً"),
}

# Common feature phrases (lower-case English key -> Arabic). Used both for translation in the
# template writer and, via FEATURE_CLAIMS in checks.py, for spotting amenities the text claims.
FEATURES_AR = {
    "balcony": "شرفة",
    "private pool": "مسبح خاص",
    "shared pool": "مسبح مشترك",
    "swimming pool": "مسبح",
    "pool": "مسبح",
    "gym": "صالة رياضية",
    "maid's room": "غرفة خادمة",
    "maids room": "غرفة خادمة",
    "study": "غرفة مكتب",
    "built-in wardrobes": "خزائن مدمجة",
    "walk-in closet": "غرفة ملابس",
    "covered parking": "موقف مغطى",
    "concierge": "خدمة الكونسيرج",
    "24/7 security": "أمن على مدار الساعة",
    "security": "أمن",
    "central a/c": "تكييف مركزي",
    "chiller free": "تبريد مجاني",
    "kids' play area": "منطقة ألعاب للأطفال",
    "children's play area": "منطقة ألعاب للأطفال",
    "private garden": "حديقة خاصة",
    "garden": "حديقة",
    "beach access": "وصول إلى الشاطئ",
    "private beach": "شاطئ خاص",
    "metro access": "قرب المترو",
    "pets allowed": "يُسمح بالحيوانات الأليفة",
    "storage room": "غرفة تخزين",
    "laundry room": "غرفة غسيل",
    "upgraded kitchen": "مطبخ مُحدَّث",
    "open kitchen": "مطبخ مفتوح",
    "vacant on transfer": "شاغرة عند نقل الملكية",
    "tenanted": "مؤجرة حالياً",
    "smart home": "منزل ذكي",
    "rooftop terrace": "تراس على السطح",
    "terrace": "تراس",
    "jacuzzi": "جاكوزي",
    "sauna": "ساونا",
    "bbq area": "منطقة شواء",
    "high floor": "طابق مرتفع",
    "low floor": "طابق منخفض",
    "corner unit": "وحدة زاوية",
}

VIEWS_AR = {
    "sea view": "إطلالة على البحر",
    "marina view": "إطلالة على المارينا",
    "burj khalifa view": "إطلالة على برج خليفة",
    "canal view": "إطلالة على القناة",
    "golf course view": "إطلالة على ملعب الغولف",
    "golf view": "إطلالة على ملعب الغولف",
    "park view": "إطلالة على الحديقة",
    "pool view": "إطلالة على المسبح",
    "community view": "إطلالة على المجتمع السكني",
    "city view": "إطلالة على المدينة",
    "skyline view": "إطلالة على أفق المدينة",
    "creek view": "إطلالة على الخور",
    "lake view": "إطلالة على البحيرة",
    "garden view": "إطلالة على الحديقة",
}


def community_ar(name: str, override: str = "") -> str:
    if override:
        return override
    return COMMUNITY_AR.get(name.strip().lower(), name)


def feature_ar(feature: str) -> str:
    return FEATURES_AR.get(feature.strip().lower(), feature)


def view_ar(view: str, override: str = "") -> str:
    if override:
        return override
    return VIEWS_AR.get(view.strip().lower(), view)


def bedrooms_en(n: int | None) -> str:
    if n is None:
        return ""
    if n == 0:
        return "Studio"
    return f"{n}-Bedroom"


def bedrooms_ar(n: int | None, genitive: bool = False) -> str:
    """Arabic phrase for bedroom count with correct dual/plural agreement.

    ``genitive=True`` gives the form used after a preposition ("شقة من غرفتي نوم").
    """
    if n is None:
        return ""
    if n == 0:
        return "استوديو"
    if n == 1:
        return "غرفة نوم واحدة"
    if n == 2:
        return "غرفتي نوم" if genitive else "غرفتا نوم"
    if 3 <= n <= 10:
        return f"{n} غرف نوم"
    return f"{n} غرفة نوم"


def bathrooms_ar(n: int | None) -> str:
    if n is None:
        return ""
    if n == 1:
        return "حمام واحد"
    if n == 2:
        return "حمامان"
    if 3 <= n <= 10:
        return f"{n} حمامات"
    return f"{n} حماماً"


def parking_ar(n: int | None) -> str:
    if not n:
        return ""
    if n == 1:
        return "موقف سيارة واحد"
    if n == 2:
        return "موقفا سيارات"
    if 3 <= n <= 10:
        return f"{n} مواقف سيارات"
    return f"{n} موقفاً"


def cheques_ar(n: int) -> str:
    if n == 1:
        return "شيك واحد"
    if n == 2:
        return "شيكان"
    if 3 <= n <= 10:
        return f"{n} شيكات"
    return f"{n} شيكاً"
