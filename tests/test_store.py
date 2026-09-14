from pathlib import Path

from kap_alert.models import Disclosure
from kap_alert.store import DisclosureStore


def _item(index: int) -> Disclosure:
    return Disclosure(
        disclosure_index=index,
        publish_date="14.09.2026 10:00:00",
        company="ÖRNEK A.Ş.",
        stock_codes="ORNEK",
        subject="Özel Durum Açıklaması (Genel)",
        summary="Yeni sözleşme",
        disclosure_class="ODA",
        disclosure_type="ODA",
        disclosure_category="ODA",
    )


def test_store_deduplicates(tmp_path: Path) -> None:
    store = DisclosureStore(tmp_path / "kap.db")
    first = _item(100)
    second = _item(101)
    assert store.unseen([first, second]) == [first, second]
    store.mark(first, matched=True, categories=("sozlesme",))
    assert store.is_seen(100)
    assert store.unseen([first, second]) == [second]
    store.mark(first, matched=True, categories=("sozlesme",))
    assert store.count() == 1
    store.close()
