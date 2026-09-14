import json
from datetime import datetime
from pathlib import Path
from kap_alert.config import Settings
from kap_alert.filters import NewsFilter
from kap_alert.models import Disclosure, ISTANBUL
from kap_alert.notifier import Notifier
from kap_alert.store import DisclosureStore

FIXTURES = Path(__file__).parent / "fixtures"
FILTERS = Path("src/kap_alert/filters.yaml")


class FakeKap:
    def __init__(self, rows: list[dict], bodies: dict[int, str] | None = None) -> None:
        self.rows = rows
        self.bodies = bodies or {}
        self.body_calls: list[int] = []

    def list_disclosures(self, from_date, to_date):
        return [Disclosure.from_list_row(row) for row in self.rows]

    def fetch_body(self, disclosure_index: int) -> str:
        self.body_calls.append(disclosure_index)
        return self.bodies.get(disclosure_index, "")


class FakeMailer:
    def __init__(self) -> None:
        self.sent: list = []

    def send(self, disclosures) -> None:
        self.sent.append(disclosures)


def _settings(tmp_path: Path, **kwargs) -> Settings:
    values = dict(
        db_path=tmp_path / "kap.db",
        filters_path=FILTERS,
        dry_run=True,
        notify_on_start=True,
        lookback_days=1,
        fetch_body=True,
        smtp_from="alerts@example.com",
        alert_to="user@example.com",
        smtp_host="localhost",
    )
    values.update(kwargs)
    return Settings(**values)


def test_notifier_emails_only_new_positive_items(tmp_path: Path) -> None:
    sample = json.loads((FIXTURES / "bycriteria_sample.json").read_text())
    client = FakeKap(
        sample,
        bodies={
            1662168: "İstanbul Ümraniye Tepeüstü Sözleşme İmzalanması",
            1662175: "Üretim tesislerimizi çeşitlendirme ve kapasite artırımı",
            1662137: "Planlanan devralınma süreci hakkında açıklama",
        },
    )
    mailer = FakeMailer()
    notifier = Notifier(
        _settings(tmp_path),
        client=client,
        store=DisclosureStore(tmp_path / "kap.db"),
        news_filter=NewsFilter.from_yaml(FILTERS),
        mailer=mailer,
        now=lambda: datetime(2026, 9, 14, 11, 0, tzinfo=ISTANBUL),
    )
    matches = notifier.run_once()
    tickers = {item.tickers for item, _ in matches}
    assert "EKGYO" in tickers
    assert mailer.sent and len(mailer.sent[0]) == len(matches)
    noise = [row for row in sample if row["subject"] == "Pay Bazında Devre Kesici Bildirimi"]
    assert noise
    assert not any(item.subject.startswith("Pay Bazında") for item, _ in matches)

    mailer.sent.clear()
    second = notifier.run_once()
    assert second == []
    assert mailer.sent == []


def test_first_run_seeds_without_email_unless_backfill(tmp_path: Path) -> None:
    rows = [
        {
            "disclosureIndex": 1,
            "publishDate": "14.09.2026 09:00:00",
            "kapTitle": "ÖRNEK A.Ş.",
            "stockCodes": "ORNEK",
            "relatedStocks": None,
            "subject": "Özel Durum Açıklaması (Genel)",
            "summary": "Yeni sözleşme imzalandı",
            "disclosureClass": "ODA",
            "disclosureType": "ODA",
            "disclosureCategory": "ODA",
        }
    ]
    mailer = FakeMailer()
    notifier = Notifier(
        _settings(tmp_path, notify_on_start=False, backfill_minutes=0),
        client=FakeKap(rows),
        store=DisclosureStore(tmp_path / "kap.db"),
        news_filter=NewsFilter.from_yaml(FILTERS),
        mailer=mailer,
        now=lambda: datetime(2026, 9, 14, 11, 0, tzinfo=ISTANBUL),
    )
    assert notifier.run_once() == []
    assert mailer.sent == []
    assert notifier.store.is_seen(1)


def test_mail_message_contains_kap_link() -> None:
    from kap_alert.mailer import build_message

    item = Disclosure.from_list_row(
        {
            "disclosureIndex": 1662168,
            "publishDate": "14.09.2026 09:30:00",
            "kapTitle": "EMLAK KONUT",
            "stockCodes": "EKGYO",
            "relatedStocks": None,
            "subject": "Özel Durum Açıklaması (Genel)",
            "summary": "Sözleşme İmzalanması",
            "disclosureClass": "ODA",
            "disclosureType": "ODA",
            "disclosureCategory": "ODA",
        }
    )
    from kap_alert.filters import Match

    message = build_message(
        [(item, Match(True, 5, ("sozlesme",), ("Yeni sözleşme",), "test"))],
        Settings(smtp_from="a@b.com", alert_to="c@d.com"),
    )
    html = message.get_body(preferencelist=("html",)).get_content()
    assert "https://www.kap.org.tr/tr/Bildirim/1662168" in html
    assert "EKGYO" in html
