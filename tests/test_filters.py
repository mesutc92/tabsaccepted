"""Filter rules against real KAP titles and synthetic cases."""

from pathlib import Path

from kap_alert.filters import NewsFilter
from kap_alert.models import Disclosure

FILTER = NewsFilter.from_yaml(Path("src/kap_alert/filters.yaml"))


def _item(**kwargs) -> Disclosure:
    defaults = {
        "disclosure_index": 1,
        "publish_date": "14.09.2026 10:00:00",
        "company": "ÖRNEK A.Ş.",
        "stock_codes": "ORNEK",
        "subject": "Özel Durum Açıklaması (Genel)",
        "summary": "",
        "disclosure_class": "ODA",
        "disclosure_type": "ODA",
        "disclosure_category": "ODA",
    }
    defaults.update(kwargs)
    return Disclosure(**defaults)


def test_skips_circuit_breaker_noise() -> None:
    item = _item(
        subject="Pay Bazında Devre Kesici Bildirimi",
        summary="IZMDC.E işlem sırasında Pay Bazında Devre Kesici Uygulaması",
        stock_codes="IZMDC",
    )
    assert FILTER.is_noise(item)
    assert not FILTER.evaluate(item).matched


def test_skips_insider_trade_and_test() -> None:
    assert FILTER.is_noise(_item(subject="Pay Alım Satım Bildirimi", stock_codes="EGEPO"))
    assert FILTER.is_noise(_item(subject="Test Bildirimi", stock_codes="KTEST"))


def test_matches_contract_signing() -> None:
    item = _item(
        stock_codes="EKGYO",
        summary="İstanbul Ümraniye Tepeüstü Sözleşme İmzalanması",
    )
    match = FILTER.evaluate(item)
    assert match.matched
    assert "sozlesme" in match.categories


def test_matches_tender_win() -> None:
    item = _item(summary="Belediye ihaleyi kazandık, yüklenici seçildik")
    match = FILTER.evaluate(item)
    assert match.matched
    assert "ihale" in match.categories


def test_matches_dividend_and_profit() -> None:
    temettu = FILTER.evaluate(_item(summary="Nakit temettü dağıtım kararı"))
    kar = FILTER.evaluate(_item(summary="2026/6 net kâr artışı ve EBITDA rekoru"))
    assert temettu.matched
    assert kar.matched


def test_matches_merger_and_buyback_subject() -> None:
    merger = FILTER.evaluate(
        _item(summary="Pusula Finans Holding A.Ş. Paylarının Planlanan Devralınma Süreci")
    )
    buyback = FILTER.evaluate(
        _item(
            subject="Payların Geri Alınmasına İlişkin Bildirim",
            summary="Pay Geri Alım Programı Kararı",
            stock_codes="TTKOM",
        )
    )
    assert merger.matched
    assert "birlesme_devralma" in merger.categories
    assert buyback.matched
    assert buyback.reason == "öncelikli KAP konusu"


def test_matches_investment_capacity_from_body() -> None:
    item = _item(
        stock_codes="SMRTG",
        summary="Üretim Tesislerimizin Çeşitlendirilmesi",
        body_text="Üretim tesislerimizi geliştirme ve kapasite artırımı planlanmaktadır.",
    )
    match = FILTER.evaluate(item)
    assert match.matched
    assert "yatirim_kapasite" in match.categories


def test_vetoes_bankruptcy_even_with_contract_words() -> None:
    item = _item(summary="Sözleşme imzalandı ancak konkordato sürecine girildi")
    match = FILTER.evaluate(item)
    assert match.vetoed
    assert not match.matched


def test_requires_stock_code_when_configured() -> None:
    item = _item(stock_codes="", related_stocks="", summary="Yeni sözleşme imzalandı")
    assert not FILTER.evaluate(item).matched


def test_skips_buyback_termination() -> None:
    item = _item(
        subject="Payların Geri Alınmasına İlişkin Bildirim",
        summary="Pay Geri Alım Programının Sonlandırılması",
        stock_codes="TTKOM",
    )
    match = FILTER.evaluate(item)
    assert not match.matched


def test_credit_rating_requires_upgrade_language() -> None:
    routine = FILTER.evaluate(
        _item(
            subject="Kredi Derecelendirmesi",
            summary="Kredi Derecelendirme Notlarına İlişkin Bildirim 2026",
            stock_codes="EMIRV",
        )
    )
    upgrade = FILTER.evaluate(
        _item(
            subject="Kredi Derecelendirmesi",
            summary="Uzun vadeli ulusal notu yükseltildi, görünüm pozitif",
            stock_codes="EMIRV",
        )
    )
    assert not routine.matched
    assert upgrade.matched
    assert "kredi_notu" in upgrade.categories


def test_needs_body_only_for_oda_and_ratings() -> None:
    oda = _item(subject="Özel Durum Açıklaması (Genel)")
    buyback = _item(subject="Payların Geri Alınmasına İlişkin Bildirim")
    noise = _item(subject="Pay Bazında Devre Kesici Bildirimi")
    rating = _item(subject="Kredi Derecelendirmesi")
    assert FILTER.needs_body(oda)
    assert FILTER.needs_body(rating)
    assert not FILTER.needs_body(buyback)
    assert not FILTER.needs_body(noise)
