"""Official sources behind the compliance checks.

Every compliance finding points to one of these keys. Sources were read on the `checked` date; rules
change, so re-check them before relying on this tool. This is not legal advice.
"""

from __future__ import annotations

CHECKED = "2026-11-04"

SOURCES: dict[str, dict[str, str]] = {
    "rera-circular-2-2022": {
        "title": "RERA Circular 2-2022: Terms and conditions for real estate advertisements (20/07/2022)",
        "title_ar": "تعميم مؤسسة التنظيم العقاري رقم 2-2022: الشروط والأحكام الخاصة بالإعلانات العقارية",
        "publisher": "Dubai Land Department / RERA",
        "url": "https://dubailand.gov.ae/media/daylptgk/%D8%A7%D9%84%D8%B4%D8%B1%D9%88%D8%B7-%D9%88%D8%A7%D9%84%D8%A7%D8%AD%D9%83%D8%A7%D9%85-%D8%A7%D9%84%D8%AE%D8%A7%D8%B5%D8%A9-%D8%A8%D8%A7%D9%84%D8%A5%D8%B9%D9%84%D8%A7%D9%86%D8%A7%D8%AA-%D8%A7%D9%84%D8%B9%D9%82%D8%A7%D8%B1%D9%8A%D8%A9-1.pdf",
        "summary": (
            "Applies to ads on any channel incl. property portals and social media. (1) official RERA permit, "
            "permit number displayed on the ad; (2) company name on written or visual ads; (3) off-plan ads show "
            "developer name, project name, project number, project location and escrow account number; "
            "(4) the advertiser is responsible for the validity and credibility of the content, and must not add "
            "information not approved in the permit; (5) promotional campaigns (free benefits, discounts, fee "
            "exemptions) need a separate promotional campaign permit; (6) no direct-call marketing unless the "
            "person is on the RERA green list; (7) violations are issued for non-compliance."
        ),
    },
    "dld-2020-permits": {
        "title": "DLD fines 10 real estate companies and warns another 30 for not adhering to advertising requirements (20 Oct 2020)",
        "title_ar": "دائرة الأراضي والأملاك تخالف 10 شركات عقارية وتنذر 30 أخرى لعدم الالتزام بشروط الإعلانات",
        "publisher": "Dubai Land Department",
        "url": "https://dubailand.gov.ae/en/news-media/dld-fines-10-real-estate-companies-and-warns-another-30-for-not-adhering-to-advertising-requirements/",
        "summary": (
            "Permits must be obtained through the Trakheesi system before any marketing campaign; the permit "
            "number must be included in all real estate ads; violations include ads without a permit, misuse of "
            "permit numbers and expired permits; fines are progressive and start from AED 50,000."
        ),
    },
    "dld-2024-qr": {
        "title": "DLD fines 30 real estate companies for failing to comply with the terms and conditions specified in real estate advertisements (8 Feb 2024)",
        "title_ar": "الدائرة تخالف 30 شركة عقارية لعدم التزامها بشروط الإعلانات العقارية",
        "publisher": "Dubai Land Department",
        "url": "https://dubailand.gov.ae/en/news-media/dld-fines-30-real-estate-companies-for-failing-to-comply-with-the-terms-and-conditions-specified-in-real-estate-advertisements",
        "summary": (
            "Ads must carry accurate and correct information; it is obligatory to include a QR code so investors "
            "can verify the advertised property data; the public is told not to engage with ads without a permit "
            "and QR code. 30 companies were fined AED 50,000 each."
        ),
    },
    "dld-2024-256-brokers": {
        "title": "Dubai Land Department fines 256 brokers for failing to comply with advertising terms and conditions (17 Jul 2024)",
        "title_ar": "دائرة الأراضي والأملاك تخالف 256 وسيطاً لعدم التزامهم بشروط الإعلانات",
        "publisher": "Dubai Land Department",
        "url": "https://dubailand.gov.ae/en/news-media/dubai-land-department-fines-256-brokers-for-failing-to-comply-with-advertising-terms-and-conditions-over-the-past-six-months",
        "summary": (
            "The QR code must meet the approved specifications and be readable when scanned, and the ad's data "
            "must match what the QR code / permit authorises."
        ),
    },
    "dld-2016-trakheesi": {
        "title": "RERA makes new real estate permit e-service announcement (3 Oct 2016)",
        "title_ar": "مؤسسة التنظيم العقاري تعلن عن خدمة إلكترونية جديدة لتصاريح الإعلانات العقارية",
        "publisher": "Dubai Land Department / RERA",
        "url": "https://dubailand.gov.ae/en/news-media/real-estate-regulatory-agency-makes-new-real-estate-permit-e-service-announcement",
        "summary": (
            "No company may advertise Dubai properties from within or outside the Emirate without a permit; "
            "announcements not bearing a real estate permit number are dismissed; offenders pay AED 50,000."
        ),
    },
    "dld-brokerage-guide-2024": {
        "title": "Real Estate Brokerage Practice Guide 2024, section 7 'Real Estate Permits'",
        "title_ar": "دليل ممارسة مهنة الوساطة العقارية 2024، القسم 7",
        "publisher": "Dubai Land Department",
        "url": "https://dubailand.gov.ae/media/i31iv1n0/real_estate_brokerage_practice_guide_2024.pdf",
        "summary": (
            "Brokerages obtain a permit for any real estate advertisement or marketing material through "
            "Trakheesi, and the permit number must be displayed on the ad."
        ),
    },
    "gulfnews-2024-just-sold": {
        "title": "Dubai brokers will need to follow new strict rule on 'Just Sold' ads (Gulf News, 13 Dec 2024) - press report, not an official DLD page",
        "title_ar": "تقرير صحفي (غلف نيوز) عن تعميم دائرة الأراضي بشأن إعلانات «تم البيع»",
        "publisher": "Gulf News (secondary source)",
        "url": "https://gulfnews.com/business/property/dubai-brokers-will-need-to-follow-new-strict-rule-on-just-sold-ads-1.1734060989359",
        "summary": (
            "Reports a DLD circular: 'sold' ads only after the property is formally transferred to the buyer; "
            "all details in the advert must be accurate to the property; duplicate and ghost listings are banned."
        ),
    },
}


def cite(key: str) -> dict[str, str]:
    s = SOURCES[key]
    return {"key": key, "title": s["title"], "url": s["url"], "publisher": s["publisher"]}
