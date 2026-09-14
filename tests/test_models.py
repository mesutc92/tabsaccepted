"""Tests for Turkish text folding, HTML stripping and date parsing."""

from datetime import datetime

from kap_alert.models import (
    Disclosure,
    fold_tr,
    html_to_text,
    parse_publish_date,
)


def test_fold_tr_matches_i_and_ihale_variants() -> None:
    assert fold_tr("İHALE") == "ihale"
    assert fold_tr("IHALEYI") == "ihaleyi"
    assert "sozlesme" in fold_tr("Sözleşme İmzalanması")
    assert "kar payi" in fold_tr("Kâr Payı")


def test_html_to_text_strips_tags_and_field_codes() -> None:
    raw = (
        "<table><tr><td>Özet Bilgi</td><td>Yeni sözleşme</td></tr>"
        "<tr><td>oda_ExplanationTextBlock| Açıklama metni</td></tr></table>"
    )
    text = html_to_text(raw)
    assert "Yeni sözleşme" in text
    assert "Açıklama metni" in text
    assert "oda_" not in text


def test_extract_explanation_prefers_aciklamalar_block() -> None:
    from kap_alert.models import extract_explanation

    raw = (
        "<p>[CONSOLIDATION_METHOD_TITLE]</p>"
        "<p>Hayır (No)</p>"
        "<p>Açıklamalar Explanations</p>"
        "<p>Yeni tesis yatırımı kararı alındı.</p>"
    )
    text = extract_explanation(raw)
    assert "Yeni tesis yatırımı kararı alındı." in text
    assert "CONSOLIDATION_METHOD" not in text


def test_parse_publish_date_turkish_format() -> None:
    parsed = parse_publish_date("14.09.2026 10:46:06")
    assert parsed is not None
    assert parsed == datetime(2026, 9, 14, 10, 46, 6, tzinfo=parsed.tzinfo)


def test_disclosure_from_list_row() -> None:
    item = Disclosure.from_list_row(
        {
            "disclosureIndex": 1662168,
            "publishDate": "14.09.2026 09:30:00",
            "kapTitle": "EMLAK KONUT GAYRİMENKUL YATIRIM ORTAKLIĞI A.Ş.",
            "stockCodes": "EKGYO",
            "relatedStocks": None,
            "subject": "Özel Durum Açıklaması (Genel)",
            "summary": "İstanbul Ümraniye Tepeüstü Sözleşme İmzalanması",
            "disclosureClass": "ODA",
            "disclosureType": "ODA",
            "disclosureCategory": "ODA",
        }
    )
    assert item.tickers == "EKGYO"
    assert item.disclosure_index == 1662168
    assert "1662168" in item.url
