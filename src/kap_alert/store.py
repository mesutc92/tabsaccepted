"""SQLite persistence for seen KAP disclosure indexes."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from kap_alert.models import Disclosure


class DisclosureStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_disclosures (
                disclosure_index INTEGER PRIMARY KEY,
                stock_codes TEXT,
                company TEXT,
                subject TEXT,
                summary TEXT,
                matched INTEGER NOT NULL DEFAULT 0,
                categories TEXT,
                first_seen_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def is_seen(self, disclosure_index: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_disclosures WHERE disclosure_index = ?",
            (disclosure_index,),
        ).fetchone()
        return row is not None

    def unseen(self, disclosures: list[Disclosure]) -> list[Disclosure]:
        return [item for item in disclosures if not self.is_seen(item.disclosure_index)]

    def mark(
        self,
        disclosure: Disclosure,
        *,
        matched: bool,
        categories: tuple[str, ...] = (),
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO seen_disclosures (
                disclosure_index, stock_codes, company, subject, summary,
                matched, categories, first_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                disclosure.disclosure_index,
                disclosure.tickers,
                disclosure.company,
                disclosure.subject,
                disclosure.summary,
                1 if matched else 0,
                ",".join(categories),
                now,
            ),
        )
        self._conn.commit()

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM seen_disclosures"
        ).fetchone()
        return int(row["n"]) if row else 0

    def close(self) -> None:
        self._conn.close()
