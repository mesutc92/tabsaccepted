"""KAP disclosure models and HTML/text helpers."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")
KAP_DETAIL_URL = "https://www.kap.org.tr/tr/Bildirim/{index}"

_TR_FOLD = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
        "â": "a",
        "î": "i",
        "û": "u",
        "Ç": "c",
        "Ğ": "g",
        "İ": "i",
        "I": "i",
        "Ö": "o",
        "Ş": "s",
        "Ü": "u",
        "Â": "a",
        "Î": "i",
        "Û": "u",
    }
)


def fold_tr(text: str) -> str:
    """Lowercase and fold Turkish characters so 'İHALE' matches 'ihale'."""
    return (text or "").translate(_TR_FOLD).lower()


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._chunks.append(data.strip())

    def text(self) -> str:
        return " ".join(self._chunks)


_FIELD_CODE_RE = re.compile(r"\boda_[A-Za-z0-9_|]+\b")
_PLACEHOLDER_RE = re.compile(r"\[CONSOLIDATION_METHOD[^\]]*\]")
_SPACE_RE = re.compile(r"\s+")
_EXPLANATION_MARKERS = (
    "Açıklamalar Explanations",
    "Açıklamalar",
    "Explanations",
)


def html_to_text(raw: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html.unescape(raw or ""))
    parser.close()
    text = parser.text()
    text = _FIELD_CODE_RE.sub(" ", text)
    text = _PLACEHOLDER_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def extract_explanation(raw_html: str) -> str:
    """Return the KAP explanation block when present, otherwise full plain text."""
    text = html_to_text(raw_html)
    for marker in _EXPLANATION_MARKERS:
        pos = text.find(marker)
        if pos != -1:
            rest = text[pos + len(marker) :].lstrip(" |:-")
            if rest:
                return rest
    return text


def parse_publish_date(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    formats = (
        "%d.%m.%Y %H:%M:%S",
        "%Y.%m.%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
    )
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=ISTANBUL)
        except ValueError:
            continue
    return None


@dataclass
class Disclosure:
    disclosure_index: int
    publish_date: str
    company: str
    stock_codes: str
    subject: str
    summary: str
    disclosure_class: str
    disclosure_type: str
    disclosure_category: str
    related_stocks: str = ""
    body_text: str = ""
    published_at: datetime | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def tickers(self) -> str:
        return self.stock_codes or self.related_stocks

    @property
    def url(self) -> str:
        return KAP_DETAIL_URL.format(index=self.disclosure_index)

    @property
    def searchable_text(self) -> str:
        return " ".join(
            part
            for part in (self.subject, self.summary, self.company, self.body_text)
            if part
        )

    @classmethod
    def from_list_row(cls, row: dict[str, Any]) -> Disclosure:
        publish = str(row.get("publishDate") or "")
        stocks = str(row.get("stockCodes") or "").strip()
        related = str(row.get("relatedStocks") or "").strip()
        return cls(
            disclosure_index=int(row["disclosureIndex"]),
            publish_date=publish,
            company=str(row.get("kapTitle") or "").strip(),
            stock_codes=stocks,
            related_stocks=related,
            subject=str(row.get("subject") or "").strip(),
            summary=str(row.get("summary") or "").strip(),
            disclosure_class=str(row.get("disclosureClass") or "").strip(),
            disclosure_type=str(row.get("disclosureType") or "").strip(),
            disclosure_category=str(row.get("disclosureCategory") or "").strip(),
            published_at=parse_publish_date(publish),
            extra=row,
        )
