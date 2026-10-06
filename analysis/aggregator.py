"""Aggregation and opportunity ranking engine for Google Photos retrieval failures."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import AnalysisConfig
from core.schemas import (
    AggregationResult,
    CategoryAggregation,
    EnrichedRecord,
)

logger = logging.getLogger("discovery_engine")

# ---------------------------------------------------------------------------
# Signal Detection Constants
# ---------------------------------------------------------------------------
FRUSTRATION_KEYWORDS = [
    r"\b(frustrated|frustrating|frustration)\b",
    r"\b(terrible|horrible|awful|garbage|useless)\b",
    r"\b(impossible|broken|ridiculous|nightmare)\b",
    r"\b(hate|hated|sucks|suck|worst)\b",
    r"\b(annoying|annoyed|drives me crazy|painful)\b",
    r"\b(waste of time|hours wasted|spent hours)\b",
    r"\b(can'?t believe|fail|failed|failing)\b",
]
COMPILED_FRUSTRATION = re.compile("|".join(FRUSTRATION_KEYWORDS), re.IGNORECASE)

CHURN_KEYWORDS = [
    r"\b(switching to|switch to|switched to)\b",
    r"\b(uninstall|uninstalled|uninstalling)\b",
    r"\b(moving to|moved to|migrating to)\b",
    r"\b(giving up|gave up|given up)\b",
    r"\b(cancelled|canceling|cancel subscription)\b",
    r"\b(deleting my account|delete google photos)\b",
    r"\b(exporting everything|export to)\b",
    r"\b(apple photos|immich|onedrive|local backup|dropbox)\b",
]
COMPILED_CHURN = re.compile("|".join(CHURN_KEYWORDS), re.IGNORECASE)

# Baseline feasibility estimates per category (higher = easier to implement)
CATEGORY_FEASIBILITY: dict[str, float] = {
    "visual_detail": 85.0,           # Modern vision models (CLIP, SigLIP) can easily detect colors & clothing
    "document_screenshot": 85.0,     # Improved OCR and document-specific parsing models
    "object_in_scene": 75.0,         # Secondary object detection / dense captioning
    "temporal_approximation": 80.0,  # Temporal range parser and relative date heuristic rules
    "people_event": 70.0,            # Graph-based co-occurrence + activity recognition
    "contextual_episodic": 65.0,     # Multi-modal LLM reasoning over scenes and episodic memory
    "emotional_association": 60.0,   # Candid vs posed classification, expression analysis
    "emergent": 70.0,                # Chronological browse & hybrid search filters
}


class Aggregator:
    """Aggregates analyzed records, computes severity & opportunity scores, and builds rankings."""

    def __init__(self, config: AnalysisConfig):
        self.config = config

    def calculate_severity(self, record: EnrichedRecord) -> float:
        """Compute composite severity score for a single record (0.0 to 1.0).

        Formula:
            severity = w_lang * lang_intensity + w_star * star_sev + w_churn * churn_sev
        """
        text = record.record.raw_text
        weights = self.config.severity_weights

        # 1. Language intensity (0.0 to 1.0)
        frustration_matches = len(COMPILED_FRUSTRATION.findall(text))
        exclamation_count = text.count("!")
        words = text.split()
        caps_words = [w for w in words if len(w) > 2 and w.isupper()]
        caps_ratio = min(1.0, len(caps_words) / max(1, len(words)) * 5)

        lang_score = min(
            1.0,
            (frustration_matches * 0.3) + min(0.3, exclamation_count * 0.1) + (caps_ratio * 0.4),
        )

        # 2. Star rating severity (1 star -> 1.0, 5 stars -> 0.0)
        if record.record.rating is not None:
            star_score = max(0.0, min(1.0, (5 - record.record.rating) / 4.0))
        else:
            # Default for Reddit/Forum comments where star rating is absent
            star_score = 0.6 if frustration_matches > 0 else 0.4

        # 3. Churn signal (0.0 or 1.0)
        churn_score = 1.0 if COMPILED_CHURN.search(text) else 0.0

        w_lang = weights.get("language_intensity", 0.4)
        w_star = weights.get("star_rating", 0.3)
        w_churn = weights.get("churn_signal", 0.3)

        composite = (w_lang * lang_score) + (w_star * star_score) + (w_churn * churn_score)
        return round(composite, 4)

    def aggregate(
        self,
        records: list[EnrichedRecord],
        total_collected: int = 0,
        total_discarded: int = 0,
    ) -> AggregationResult:
        """Run full aggregation and ranking across all analyzed records."""
        category_records: dict[str, list[tuple[EnrichedRecord, float]]] = {}
        sources_seen = set()
        dates: list[datetime] = []

        # Group by category and compute record severity
        for rec in records:
            sources_seen.add(rec.record.source_type.value)
            if rec.record.date:
                dt = rec.record.date
                dates.append(dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))

            severity = self.calculate_severity(rec)
            cats = rec.categorization.failure_types if rec.categorization else ["emergent"]

            for cat in cats:
                category_records.setdefault(cat, []).append((rec, severity))

        total_relevant = len(records)
        total_coll = total_collected if total_collected > 0 else total_relevant
        max_vol = max((len(items) for items in category_records.values()), default=1)

        category_aggregations: list[CategoryAggregation] = []

        for cat_name, items in category_records.items():
            count = len(items)
            pct = round((count / max(1, total_relevant)) * 100, 2)

            # Average severity (0 - 100)
            avg_sev = float(sum(s for _, s in items) / count * 100)

            # Volume score normalized (0 - 100)
            vol_score = (count / max_vol) * 100

            # Feasibility score
            feasibility = CATEGORY_FEASIBILITY.get(cat_name, 70.0)

            # Opportunity score: 0.4 * vol + 0.4 * sev + 0.2 * feas
            w_vol = self.config.opportunity_weights.get("volume", 0.4)
            w_sev = self.config.opportunity_weights.get("severity", 0.4)
            w_feas = self.config.opportunity_weights.get("feasibility", 0.2)
            opp_score = round(
                (w_vol * vol_score) + (w_sev * avg_sev) + (w_feas * feasibility), 2
            )

            # Sort items by severity to find top 5 representative quotes
            items.sort(key=lambda x: x[1], reverse=True)
            top_quotes = []
            for r, s in items[:5]:
                top_quotes.append({
                    "record_id": r.record.record_id,
                    "text": r.record.raw_text,
                    "source_type": r.record.source_type.value,
                    "source_url": r.record.source_url or "",
                    "rating": str(r.record.rating) if r.record.rating else "N/A",
                    "severity_score": f"{s * 100:.1f}",
                    "failure_description": r.categorization.description if r.categorization else "",
                })

            # Memory attribute frequencies
            remembered_freq: dict[str, int] = {}
            forgotten_freq: dict[str, int] = {}
            search_strategies: set[str] = set()

            for r, _ in items:
                if r.memory_model:
                    for k, v in r.memory_model.remembered.model_dump().items():
                        if v:
                            remembered_freq[k] = remembered_freq.get(k, 0) + len(v)
                    for k, v in r.memory_model.forgotten.model_dump().items():
                        if v:
                            forgotten_freq[k] = forgotten_freq.get(k, 0) + 1
                    for strat in r.memory_model.search_attempts.strategies:
                        if strat:
                            search_strategies.add(strat)

            category_aggregations.append(
                CategoryAggregation(
                    category=cat_name,
                    volume_count=count,
                    volume_percentage=pct,
                    severity_score=round(avg_sev, 2),
                    opportunity_score=opp_score,
                    representative_quotes=top_quotes,
                    remembered_frequency=remembered_freq,
                    forgotten_frequency=forgotten_freq,
                    common_search_strategies=sorted(list(search_strategies)),
                )
            )

        # Sort categories by opportunity score descending
        category_aggregations.sort(key=lambda c: c.opportunity_score, reverse=True)

        date_range = {}
        if dates:
            date_range = {
                "start": min(dates).isoformat(),
                "end": max(dates).isoformat(),
            }

        return AggregationResult(
            total_records_collected=total_coll,
            total_records_relevant=total_relevant,
            total_records_discarded=total_discarded,
            sources_analyzed=sorted(list(sources_seen)),
            date_range=date_range,
            categories=category_aggregations,
            analysis_timestamp=datetime.now(timezone.utc),
        )
