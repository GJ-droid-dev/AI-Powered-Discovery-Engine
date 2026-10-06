"""Evidence Library — searchable, exportable index of user quotes, source attributions, and cognitive memory models."""

from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

from core.schemas import EnrichedRecord
from analysis.aggregator import Aggregator

logger = logging.getLogger("discovery_engine")


class EvidenceLibrary:
    """Stores, searches, and exports the evidence library of analyzed user feedback."""

    def __init__(self):
        self.entries: list[dict[str, Any]] = []

    def build_from_records(
        self, records: list[EnrichedRecord], aggregator: Aggregator | None = None
    ) -> None:
        """Build library entries from enriched analyzed records."""
        self.entries = []

        for idx, rec in enumerate(records):
            sev_score = (
                aggregator.calculate_severity(rec) * 100
                if aggregator
                else 50.0
            )

            # Summaries
            cats = rec.categorization.failure_types if rec.categorization else ["emergent"]
            desc = rec.categorization.description if rec.categorization else ""

            remembered_items = []
            if rec.memory_model:
                for attr, vals in rec.memory_model.remembered.model_dump().items():
                    if vals:
                        remembered_items.append(f"{attr}: {', '.join(vals)}")
            remembered_str = " | ".join(remembered_items)

            forgotten_items = []
            if rec.memory_model:
                for attr, flag in rec.memory_model.forgotten.model_dump().items():
                    if flag:
                        forgotten_items.append(attr.replace("_", " "))
            forgotten_str = ", ".join(forgotten_items)

            kw_tried = (
                ", ".join(rec.memory_model.search_attempts.keywords_tried)
                if rec.memory_model
                else ""
            )

            entry = {
                "quote_id": rec.record.record_id,
                "text": rec.record.raw_text,
                "source_type": rec.record.source_type.value,
                "source_url": rec.record.source_url or "",
                "date": rec.record.date.isoformat() if rec.record.date else "",
                "rating": rec.record.rating if rec.record.rating is not None else "N/A",
                "categories": cats,
                "category_primary": cats[0] if cats else "emergent",
                "severity_score": round(sev_score, 1),
                "failure_description": desc,
                "remembered_summary": remembered_str,
                "forgotten_summary": forgotten_str,
                "keywords_tried": kw_tried,
            }
            self.entries.append(entry)

        logger.info(f"Built EvidenceLibrary with {len(self.entries)} entries")

    def export_json(self, path: Path | str) -> None:
        """Export evidence library to formatted JSON."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, indent=2, ensure_ascii=False)
        logger.info(f"Exported evidence library JSON to {target}")

    def export_csv(self, path: Path | str) -> None:
        """Export evidence library to CSV."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        if not self.entries:
            return

        headers = [
            "quote_id",
            "source_type",
            "rating",
            "severity_score",
            "category_primary",
            "categories",
            "text",
            "failure_description",
            "remembered_summary",
            "forgotten_summary",
            "keywords_tried",
            "source_url",
            "date",
        ]

        with open(target, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            for entry in self.entries:
                row = entry.copy()
                row["categories"] = "; ".join(entry["categories"])
                writer.writerow(row)

        logger.info(f"Exported evidence library CSV to {target}")

    def search(
        self,
        query: str,
        category: str | None = None,
        source_type: str | None = None,
        min_severity: float = 0.0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search evidence entries by keyword query, category filter, and severity threshold.

        Returns:
            Ranked list of matching entries with highlighted snippets and relevance score.
        """
        if not query.strip() and not category and not source_type:
            # Return top entries by severity
            filtered = [e for e in self.entries if e["severity_score"] >= min_severity]
            filtered.sort(key=lambda e: e["severity_score"], reverse=True)
            return filtered[:limit]

        query_tokens = [w.lower() for w in re.findall(r"\w+", query) if len(w) > 1]
        matches: list[tuple[dict[str, Any], float]] = []

        for entry in self.entries:
            # Filter by severity
            if entry["severity_score"] < min_severity:
                continue

            # Filter by category
            if category and category.lower() not in [c.lower() for c in entry["categories"]]:
                continue

            # Filter by source
            if source_type and entry["source_type"].lower() != source_type.lower():
                continue

            score = 0.0
            text_lower = entry["text"].lower()
            desc_lower = entry["failure_description"].lower()
            rem_lower = entry["remembered_summary"].lower()

            if not query_tokens:
                score = entry["severity_score"]
            else:
                for token in query_tokens:
                    if token in text_lower:
                        score += 3.0
                    if token in desc_lower:
                        score += 4.0
                    if token in rem_lower:
                        score += 2.0
                    if any(token in c.lower() for c in entry["categories"]):
                        score += 5.0

            if score > 0:
                # Add severity weight
                final_score = score + (entry["severity_score"] / 20.0)
                matches.append((entry, final_score))

        matches.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in matches[:limit]]
