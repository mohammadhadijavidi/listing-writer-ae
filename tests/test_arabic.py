from listing_writer_ae import glossary as g
from listing_writer_ae.arabic import has_arabic, normalise, normalise_with_map, to_ascii_digits


def test_digits_and_separators():
    assert to_ascii_digits("٢٬٤٥٠٬٠٠٠٫٥") == "2,450,000.5"
    assert to_ascii_digits("۱۲۳") == "123"


def test_normalise_unifies_forms():
    assert normalise("أفضل") == normalise("افضل")
    assert normalise("مضمونة") == normalise("مضمونه")
    assert normalise("مُحدَّث") == "محدث"
    assert normalise("عـــائد") == normalise("عائد") == "عايد"  # hamza seat on ya -> ya


def test_map_points_back_to_original():
    text = "عـائدٌ"
    norm, idx = normalise_with_map(text)
    assert norm == normalise("عائد")
    assert text[idx[0] : idx[-1] + 1].startswith("عـائد")


def test_has_arabic():
    assert has_arabic("Dubai دبي") and not has_arabic("Dubai")


def test_bedroom_agreement():
    assert g.bedrooms_ar(1) == "غرفة نوم واحدة"
    assert g.bedrooms_ar(2) == "غرفتا نوم"
    assert g.bedrooms_ar(2, genitive=True) == "غرفتي نوم"
    assert g.bedrooms_ar(3) == "3 غرف نوم"
    assert g.bedrooms_ar(11) == "11 غرفة نوم"
    assert g.bathrooms_ar(2) == "حمامان"
    assert g.cheques_ar(4) == "4 شيكات" and g.cheques_ar(2) == "شيكان"


def test_glossary_passthrough_never_invents():
    assert g.community_ar("Dubai Marina") == "دبي مارينا"
    assert g.community_ar("JVC") == "قرية جميرا الدائرية"
    assert g.community_ar("Some New Community") == "Some New Community"
    assert g.community_ar("Dubai Marina", "مرسى دبي") == "مرسى دبي"
    assert g.feature_ar("Unknown thing") == "Unknown thing"
