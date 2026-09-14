"""Environment and file-based configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_FILTERS_PATH = Path(__file__).with_name("filters.yaml")
DEFAULT_DB_PATH = Path("data/kap.db")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class Settings:
    poll_interval_seconds: int = 60
    lookback_days: int = 1
    request_timeout_seconds: int = 20
    fetch_body: bool = True
    dry_run: bool = False
    notify_on_start: bool = False
    backfill_minutes: int = 0
    db_path: Path = DEFAULT_DB_PATH
    filters_path: Path = DEFAULT_FILTERS_PATH
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    alert_to: str = ""
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    @property
    def mail_configured(self) -> bool:
        return bool(self.smtp_host and self.alert_to and self.smtp_from)


def load_settings() -> Settings:
    filters_raw = os.getenv("KAP_FILTERS_PATH", "").strip()
    db_raw = os.getenv("KAP_DB_PATH", "").strip()
    return Settings(
        poll_interval_seconds=max(15, _env_int("KAP_POLL_INTERVAL", 60)),
        lookback_days=max(0, _env_int("KAP_LOOKBACK_DAYS", 1)),
        request_timeout_seconds=max(5, _env_int("KAP_TIMEOUT", 20)),
        fetch_body=_env_bool("KAP_FETCH_BODY", True),
        dry_run=_env_bool("KAP_DRY_RUN", False),
        notify_on_start=_env_bool("KAP_NOTIFY_ON_START", False),
        backfill_minutes=max(0, _env_int("KAP_BACKFILL_MINUTES", 0)),
        db_path=Path(db_raw) if db_raw else DEFAULT_DB_PATH,
        filters_path=Path(filters_raw) if filters_raw else DEFAULT_FILTERS_PATH,
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=_env_int("SMTP_PORT", 587),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
        smtp_from=os.getenv("SMTP_FROM", "").strip(),
        smtp_starttls=_env_bool("SMTP_STARTTLS", True),
        alert_to=os.getenv("ALERT_TO", "").strip(),
        user_agent=os.getenv("KAP_USER_AGENT", "").strip()
        or Settings.user_agent,
    )
