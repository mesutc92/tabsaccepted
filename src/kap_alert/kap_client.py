"""HTTP client for KAP public disclosure endpoints."""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Any

import requests

from kap_alert.models import Disclosure, extract_explanation

logger = logging.getLogger(__name__)

BASE_URL = "https://www.kap.org.tr"
LIST_URL = f"{BASE_URL}/tr/api/disclosure/members/byCriteria"
DETAIL_URL = f"{BASE_URL}/tr/api/notification/attachment-detail/{{index}}"
WARMUP_URL = f"{BASE_URL}/tr"


class KapError(RuntimeError):
    """Raised when KAP cannot be reached or returns unexpected data."""


class KapClient:
    def __init__(
        self,
        *,
        timeout: int = 20,
        user_agent: str = "",
        session: requests.Session | None = None,
        retries: int = 3,
    ) -> None:
        self.timeout = timeout
        self.retries = retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json, text/plain, */*",
                "Origin": BASE_URL,
            }
        )
        self._warm = False

    def warmup(self) -> None:
        response = self.session.get(
            WARMUP_URL,
            timeout=self.timeout,
            allow_redirects=True,
            headers={"Accept": "text/html,application/xhtml+xml"},
        )
        response.raise_for_status()
        self._warm = True

    def list_disclosures(self, from_date: date, to_date: date) -> list[Disclosure]:
        payload = {
            "fromDate": from_date.isoformat(),
            "toDate": to_date.isoformat(),
            "mkkMemberOidList": [],
            "subjectList": [],
        }
        data = self._request_json("POST", LIST_URL, json=payload)
        if not isinstance(data, list):
            raise KapError(f"Beklenmeyen KAP liste yanıtı: {type(data)}")
        return [Disclosure.from_list_row(row) for row in data if "disclosureIndex" in row]

    def fetch_body(self, disclosure_index: int) -> str:
        data = self._request_json(
            "GET",
            DETAIL_URL.format(index=disclosure_index),
            headers={"Referer": f"{BASE_URL}/tr/Bildirim/{disclosure_index}"},
        )
        if isinstance(data, list) and data:
            payload = data[0]
        elif isinstance(data, dict):
            payload = data
        else:
            return ""
        bodies = payload.get("disclosureBody") or []
        if isinstance(bodies, str):
            html = bodies
        else:
            html = "\n".join(str(part) for part in bodies)
        return extract_explanation(html)

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        last_error: Exception | None = None
        merged_headers = {
            "Referer": f"{BASE_URL}/tr/bildirim-sorgu",
            "Content-Type": "application/json",
        }
        if headers:
            merged_headers.update(headers)
        for attempt in range(1, self.retries + 1):
            try:
                if not self._warm:
                    self.warmup()
                response = self.session.request(
                    method,
                    url,
                    json=json,
                    headers=merged_headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                logger.warning(
                    "KAP isteği başarısız (%s/%s) %s %s: %s",
                    attempt,
                    self.retries,
                    method,
                    url,
                    exc,
                )
                self._warm = False
                if attempt < self.retries:
                    time.sleep(min(8, 2 ** attempt))
        raise KapError(f"KAP isteği başarısız: {method} {url}") from last_error
