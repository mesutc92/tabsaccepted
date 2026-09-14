"""One poll cycle: fetch, filter, persist, e-mail."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Callable

from kap_alert.config import Settings
from kap_alert.filters import Match, NewsFilter
from kap_alert.kap_client import KapClient
from kap_alert.mailer import Mailer
from kap_alert.models import Disclosure, ISTANBUL
from kap_alert.store import DisclosureStore

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(
        self,
        settings: Settings,
        *,
        client: KapClient | None = None,
        store: DisclosureStore | None = None,
        news_filter: NewsFilter | None = None,
        mailer: Mailer | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or KapClient(
            timeout=settings.request_timeout_seconds,
            user_agent=settings.user_agent,
        )
        self.store = store or DisclosureStore(settings.db_path)
        self.news_filter = news_filter or NewsFilter.from_yaml(settings.filters_path)
        self.mailer = mailer or Mailer(settings)
        self.now = now or (lambda: datetime.now(ISTANBUL))

    def run_once(self) -> list[tuple[Disclosure, Match]]:
        today = self.now().date()
        from_date = today - timedelta(days=self.settings.lookback_days)
        disclosures = self.client.list_disclosures(from_date, today)
        logger.info(
            "KAP listesi: %s kayıt (%s → %s)",
            len(disclosures),
            from_date.isoformat(),
            today.isoformat(),
        )
        first_run = self.store.count() == 0
        new_items = self.store.unseen(disclosures)
        logger.info("Yeni bildirim: %s", len(new_items))

        should_notify = True
        if first_run and not self.settings.notify_on_start:
            cutoff = None
            if self.settings.backfill_minutes > 0:
                cutoff = self.now() - timedelta(minutes=self.settings.backfill_minutes)
            else:
                should_notify = False
                logger.info(
                    "İlk çalışma: mevcut %s bildirim işaretlendi, e-posta yok "
                    "(KAP_NOTIFY_ON_START=1 veya --backfill-minutes ile geçmişi alabilirsiniz).",
                    len(new_items),
                )
            if cutoff is not None:
                skipped = 0
                kept: list[Disclosure] = []
                for item in new_items:
                    if item.published_at and item.published_at >= cutoff:
                        kept.append(item)
                    else:
                        self.store.mark(item, matched=False)
                        skipped += 1
                new_items = kept
                logger.info(
                    "İlk çalışma backfill: %s eski bildirim atlandı, %s değerlendirilecek.",
                    skipped,
                    len(new_items),
                )

        matches: list[tuple[Disclosure, Match]] = []
        for item in new_items:
            if should_notify and self.settings.fetch_body and self.news_filter.needs_body(item):
                try:
                    item.body_text = self.client.fetch_body(item.disclosure_index)
                except Exception:
                    logger.exception(
                        "Bildirim gövdesi alınamadı: %s", item.disclosure_index
                    )
            match = (
                self.news_filter.evaluate(item)
                if should_notify
                else Match(False, 0, (), (), "ilk çalıştırma tohumu")
            )
            if match.matched:
                matches.append((item, match))
                logger.info(
                    "Eşleşme: %s %s | %s | %s",
                    item.tickers,
                    item.summary or item.subject,
                    ", ".join(match.labels),
                    item.url,
                )
            self.store.mark(item, matched=match.matched, categories=match.categories)

        if matches:
            self.mailer.send(matches)
        return matches


def date_window(lookback_days: int, today: date | None = None) -> tuple[date, date]:
    today = today or datetime.now(ISTANBUL).date()
    return today - timedelta(days=lookback_days), today
