import json
from pathlib import Path

import requests

from kap_alert.kap_client import KapClient

FIXTURES = Path(__file__).parent / "fixtures"


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload) if not isinstance(payload, bytes) else ""

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, list_payload, detail_payload):
        self.headers = {}
        self.list_payload = list_payload
        self.detail_payload = detail_payload
        self.calls: list[tuple[str, str]] = []

    def get(self, url, **kwargs):
        self.calls.append(("GET", url))
        return FakeResponse({"ok": True})

    def request(self, method, url, **kwargs):
        self.calls.append((method, url))
        if "byCriteria" in url:
            return FakeResponse(self.list_payload)
        if "attachment-detail" in url:
            return FakeResponse(self.detail_payload)
        raise AssertionError(url)


def test_list_and_body_use_warmup_then_json() -> None:
    rows = json.loads((FIXTURES / "bycriteria_sample.json").read_text())
    detail = json.loads((FIXTURES / "detail_1662168.json").read_text())
    session = FakeSession(rows, detail)
    client = KapClient(session=session, retries=1)
    items = client.list_disclosures(__import__("datetime").date(2026, 9, 12), __import__("datetime").date(2026, 9, 14))
    assert len(items) == len(rows)
    assert any(item.tickers == "EKGYO" for item in items)
    body = client.fetch_body(1662168)
    assert "sözleşme" in body.lower() or "sozlesme" in body.lower() or "Sözleşme" in body or "sozlesme" in body
    assert any("byCriteria" in url for _, url in session.calls)


def test_real_contract_fixture_has_readable_explanation() -> None:
    from kap_alert.models import extract_explanation

    detail = json.loads((FIXTURES / "detail_1662168.json").read_text())
    html = "\n".join(detail[0]["disclosureBody"])
    text = extract_explanation(html)
    folded = text.lower()
    assert "sözleşme" in folded or "imza" in folded
    assert "CONSOLIDATION_METHOD" not in text
