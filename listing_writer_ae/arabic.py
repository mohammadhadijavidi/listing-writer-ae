"""Small Arabic text helpers: normalisation for matching, and digit conversion."""

from __future__ import annotations

import re

_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # harakat + tatweel
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"})
_ARABIC_CHARS = re.compile(r"[؀-ۿ]")


def to_ascii_digits(text: str) -> str:
    """Arabic-Indic and Persian digits -> 0-9; Arabic thousands/decimal separators -> , and ."""
    return text.translate(_DIGITS).replace("٬", ",").replace("٫", ".")


def normalise(text: str) -> str:
    """Normalise Arabic for *matching only* (never for display).

    Removes diacritics and tatweel, unifies alef forms, alef maqsura -> ya, ta marbuta -> ha,
    converts digits to ASCII and lower-cases Latin text.
    """
    t = _DIACRITICS.sub("", text)
    t = t.translate(_ALEF).replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    return to_ascii_digits(t).lower()


def normalise_with_map(text: str) -> tuple[str, list[int]]:
    """Like normalise(), plus a list mapping each output index to its index in ``text``."""
    out: list[str] = []
    idx: list[int] = []
    for i, ch in enumerate(text):
        n = normalise(ch)
        for c in n:
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def has_arabic(text: str) -> bool:
    return bool(_ARABIC_CHARS.search(text))
