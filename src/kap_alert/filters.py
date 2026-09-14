"""Positive-news classifier for KAP disclosures."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from kap_alert.models import Disclosure, fold_tr

DEFAULT_FILTERS_PATH = Path(__file__).with_name("filters.yaml")


@dataclass(frozen=True)
class Match:
    matched: bool
    score: int
    categories: tuple[str, ...]
    labels: tuple[str, ...]
    reason: str
    vetoed: bool = False


class NewsFilter:
    def __init__(self, rules: dict[str, Any]) -> None:
        self.require_stock_code = bool(rules.get("require_stock_code", True))
        self.min_score = int(rules.get("min_score", 3))
        self.fetch_body_for_oda = bool(rules.get("fetch_body_for_oda", True))
        self.skip_subjects = {
            fold_tr(item) for item in rules.get("skip_subjects") or []
        }
        self.skip_contains = [
            fold_tr(item) for item in rules.get("skip_subject_contains") or []
        ]
        self.always_match_subjects = {
            fold_tr(item) for item in rules.get("always_match_subjects") or []
        }
        self.categories: list[tuple[str, str, int, re.Pattern[str]]] = []
        for key, spec in (rules.get("categories") or {}).items():
            patterns = [fold_tr(p) for p in spec.get("patterns") or [] if p]
            if not patterns:
                continue
            combined = "|".join(re.escape(p) for p in patterns)
            self.categories.append(
                (
                    key,
                    str(spec.get("label") or key),
                    int(spec.get("weight", 3)),
                    re.compile(combined),
                )
            )
        veto = [fold_tr(p) for p in rules.get("veto_patterns") or [] if p]
        self.veto_re = (
            re.compile("|".join(re.escape(p) for p in veto)) if veto else None
        )
        exclude = [fold_tr(p) for p in rules.get("exclude_patterns") or [] if p]
        self.exclude_re = (
            re.compile("|".join(re.escape(p) for p in exclude)) if exclude else None
        )

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> NewsFilter:
        target = path or DEFAULT_FILTERS_PATH
        with target.open(encoding="utf-8") as handle:
            rules = yaml.safe_load(handle) or {}
        return cls(rules)

    def is_noise(self, disclosure: Disclosure) -> bool:
        subject = fold_tr(disclosure.subject)
        if subject in self.skip_subjects:
            return True
        return any(token in subject for token in self.skip_contains)

    def needs_body(self, disclosure: Disclosure) -> bool:
        if self.is_noise(disclosure):
            return False
        folded_subject = fold_tr(disclosure.subject)
        if folded_subject in self.always_match_subjects:
            return False
        if not self.fetch_body_for_oda:
            return False
        if folded_subject.startswith("kredi derecelendirme"):
            return True
        return folded_subject.startswith("ozel durum") or fold_tr(
            disclosure.disclosure_class
        ) in {"oda"}

    def evaluate(self, disclosure: Disclosure) -> Match:
        if self.require_stock_code and not disclosure.tickers:
            return Match(False, 0, (), (), "hisse kodu yok")
        if self.is_noise(disclosure):
            return Match(False, 0, (), (), "gürültü konusu")

        subject_folded = fold_tr(disclosure.subject)
        haystack = fold_tr(disclosure.searchable_text)
        if self.veto_re and self.veto_re.search(haystack):
            return Match(False, 0, (), (), "olumsuz veto", vetoed=True)
        if self.exclude_re and self.exclude_re.search(haystack):
            return Match(False, 0, (), (), "hariç tutulan kalıp")

        if subject_folded in self.always_match_subjects:
            return Match(
                True,
                10,
                ("konu_eslesmesi",),
                (disclosure.subject,),
                "öncelikli KAP konusu",
            )

        categories: list[str] = []
        labels: list[str] = []
        score = 0
        for key, label, weight, pattern in self.categories:
            if pattern.search(haystack):
                categories.append(key)
                labels.append(label)
                score += weight

        if score >= self.min_score and categories:
            return Match(
                True,
                score,
                tuple(categories),
                tuple(labels),
                "anahtar kelime eşleşmesi",
            )
        return Match(False, score, tuple(categories), tuple(labels), "eşik altı")
