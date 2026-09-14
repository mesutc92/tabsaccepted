"""CLI: `kap-alert once` / `kap-alert watch`."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from kap_alert.config import load_settings
from kap_alert.notifier import Notifier

logger = logging.getLogger(__name__)


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kap-alert",
        description=(
            "KAP'taki Borsa İstanbul bildirimlerini periyodik tarayıp "
            "pozitif etki potansiyeli olanları e-posta ile iletir."
        ),
    )
    parser.add_argument(
        "command",
        choices=("once", "watch"),
        help="once: tek tur. watch: KAP_POLL_INTERVAL saniyede bir döngü.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="watch aralığı (saniye). Varsayılan: KAP_POLL_INTERVAL veya 60.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="E-posta gönderme; eşleşmeleri konsola yaz.",
    )
    parser.add_argument(
        "--notify-on-start",
        action="store_true",
        help="İlk çalışmada da geçmişe bakmadan mevcut yeni kayıtları bildir.",
    )
    parser.add_argument(
        "--backfill-minutes",
        type=int,
        default=None,
        help="İlk çalışmada yalnızca son N dakikayı e-posta ile bildir.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    _configure_logging(args.verbose)
    settings = load_settings()
    if args.dry_run:
        settings = replace(settings, dry_run=True)
    if args.notify_on_start:
        settings = replace(settings, notify_on_start=True)
    if args.backfill_minutes is not None:
        settings = replace(settings, backfill_minutes=args.backfill_minutes)
    if args.interval is not None:
        settings = replace(settings, poll_interval_seconds=max(15, args.interval))

    if not settings.dry_run and not settings.mail_configured:
        logger.warning(
            "SMTP_HOST / SMTP_FROM / ALERT_TO tanımlı değil; dry-run moduna geçildi."
        )
        settings = replace(settings, dry_run=True)

    notifier = Notifier(settings)
    if args.command == "once":
        matches = notifier.run_once()
        logger.info("Tur bitti. Eşleşen bildirim: %s", len(matches))
        return 0

    logger.info(
        "İzleme başladı. Aralık: %s sn. Dry-run: %s",
        settings.poll_interval_seconds,
        settings.dry_run,
    )
    while True:
        try:
            matches = notifier.run_once()
            logger.info("Tur bitti. Eşleşen bildirim: %s", len(matches))
        except Exception:
            logger.exception("Tur başarısız, sonraki aralıkta tekrar denenecek.")
        time.sleep(settings.poll_interval_seconds)


def replace(settings, **changes):
    from dataclasses import replace as dc_replace

    return dc_replace(settings, **changes)


if __name__ == "__main__":
    sys.exit(main())
