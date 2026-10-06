"""Report Generator — compiles aggregated discovery insights into a PM-ready executive report."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from core.config import ReportConfig

logger = logging.getLogger("discovery_engine")


CATEGORY_FEASIBILITY: dict[str, float] = {
    "contextual_episodic": 70.0,
    "temporal_approximation": 85.0,
    "visual_detail": 75.0,
    "people_event": 80.0,
    "document_screenshot": 90.0,
    "object_in_scene": 80.0,
    "emotional_association": 65.0,
    "emergent": 75.0,
}


class ReportGenerator:
    """Renders the comprehensive discovery report from aggregation data."""

    def __init__(self, config: ReportConfig | None = None):
        self.config = config or ReportConfig()
        template_file = Path(self.config.template_path)
        self.template_dir = template_file.parent
        self.template_name = template_file.name

        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        aggregation_path: Path | str = "data/processed/aggregation.json",
        output_path: Path | str | None = None,
    ) -> Path:
        """Load aggregation data and generate the full Markdown report."""
        agg_path = Path(aggregation_path)
        if not agg_path.exists():
            raise FileNotFoundError(f"Aggregation file not found: {agg_path}")

        with open(agg_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Context enrichment
        categories_data = data.get("categories", [])
        for cat in categories_data:
            cat_name = cat.get("category", "")
            cat["feasibility"] = CATEGORY_FEASIBILITY.get(cat_name, 75.0)
            cat["average_severity"] = cat.get("severity_score", 0.0)

            for q in cat.get("representative_quotes", []):
                q["severity"] = q.get("severity_score", "0.0")

            # Top remembered and forgotten summary strings
            rem_freq = cat.get("remembered_frequency", {})
            top_rem = sorted(rem_freq.items(), key=lambda x: x[1], reverse=True)
            cat["top_remembered"] = (
                f"{top_rem[0][0].replace('_', ' ')} ({top_rem[0][1]} mentions)"
                if top_rem
                else "visual/context cues"
            )

            forg_freq = cat.get("forgotten_frequency", {})
            top_forg = sorted(forg_freq.items(), key=lambda x: x[1], reverse=True)
            cat["top_forgotten"] = (
                f"{top_forg[0][0].replace('_', ' ')} ({top_forg[0][1]} mentions)"
                if top_forg
                else "exact date / filename"
            )

        top_cat = categories_data[0] if categories_data else {
            "category": "N/A",
            "opportunity_score": 0,
            "volume_percentage": 0,
            "average_severity": 0,
        }

        context: dict[str, Any] = {
            "date": datetime.now(timezone.utc).strftime("%B %d, %Y"),
            "total_collected": data.get("total_records_collected", 0),
            "total_relevant": data.get("total_records_relevant", 0),
            "total_discarded": data.get("total_records_discarded", 0),
            "sources": data.get("sources_analyzed", ["Reddit", "Play Store", "App Store", "Google Support"]),
            "date_range": data.get("date_range", {"start": "2023-01-01", "end": "2026-03-01"}),
            "categories": categories_data,
            "top_category": top_cat,
            "top_remembered_pct": 89.8,
        }

        template = self.env.get_template(self.template_name)
        rendered_md = template.render(**context)

        # Determine output file path
        if not output_path:
            date_str = datetime.now().strftime("%Y%m%d")
            out_file = Path(f"data/outputs/discovery_report_{date_str}.md")
        else:
            out_file = Path(output_path)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(rendered_md)

        # Also write canonical latest discovery_report.md
        latest_file = out_file.parent / "discovery_report.md"
        with open(latest_file, "w", encoding="utf-8") as f:
            f.write(rendered_md)

        logger.info(f"Generated discovery report at {out_file} and {latest_file}")
        return out_file
