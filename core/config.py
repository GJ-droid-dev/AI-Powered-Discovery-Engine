"""YAML config loader — reads all config files and returns typed dataclasses.

Loads:
    config/sources.yaml   → SourcesConfig
    config/analysis.yaml  → AnalysisConfig
    config/report.yaml    → ReportConfig

All configs are loaded once at startup and passed to modules as typed objects.
No module reads config directly from disk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Data classes for typed configuration
# ---------------------------------------------------------------------------

@dataclass
class SourceParams:
    """Parameters for a single data source collector."""
    name: str = ""
    enabled: bool = True
    collector: str = ""
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SourcesConfig:
    """Configuration for all data sources."""
    sources: dict[str, SourceParams] = field(default_factory=dict)


@dataclass
class AnalysisConfig:
    """Configuration for the analysis pipeline."""
    relevance_threshold: float = 0.7
    review_threshold: float = 0.4
    min_text_length: int = 20
    severity_weights: dict[str, float] = field(default_factory=lambda: {
        "language_intensity": 0.4,
        "star_rating": 0.3,
        "churn_signal": 0.3,
    })
    opportunity_weights: dict[str, float] = field(default_factory=lambda: {
        "volume": 0.4,
        "severity": 0.4,
        "feasibility": 0.2,
    })
    seed_taxonomy: list[str] = field(default_factory=lambda: [
        "contextual_episodic",
        "temporal_approximation",
        "visual_detail",
        "people_event",
        "document_screenshot",
        "object_in_scene",
        "emotional_association",
    ])
    batch_size: int = 5
    llm_temperature: float = 0.0
    llm_model: str = "gemini-2.0-flash"


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    template_path: str = "reports/templates/report_template.md"
    output_format: str = "markdown"
    include_charts: bool = True
    max_quotes_per_category: int = 5


@dataclass
class AppConfig:
    """Root configuration object holding all sub-configs."""
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    data_dir: str = "./data"
    log_level: str = "INFO"
    dry_run: bool = True


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    """Load a YAML file and return its contents as a dict."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _parse_sources(raw: dict) -> SourcesConfig:
    """Parse raw YAML dict into SourcesConfig."""
    sources = {}
    for name, cfg in raw.get("sources", {}).items():
        sources[name] = SourceParams(
            name=name,
            enabled=cfg.get("enabled", True),
            collector=cfg.get("collector", ""),
            params=cfg.get("params", {}),
        )
    return SourcesConfig(sources=sources)


def _parse_analysis(raw: dict) -> AnalysisConfig:
    """Parse raw YAML dict into AnalysisConfig."""
    config = AnalysisConfig()
    if "relevance_threshold" in raw:
        config.relevance_threshold = raw["relevance_threshold"]
    if "review_threshold" in raw:
        config.review_threshold = raw["review_threshold"]
    if "min_text_length" in raw:
        config.min_text_length = raw["min_text_length"]
    if "severity_weights" in raw:
        config.severity_weights = raw["severity_weights"]
    if "opportunity_weights" in raw:
        config.opportunity_weights = raw["opportunity_weights"]
    if "seed_taxonomy" in raw:
        config.seed_taxonomy = raw["seed_taxonomy"]
    if "batch_size" in raw:
        config.batch_size = raw["batch_size"]
    if "llm_temperature" in raw:
        config.llm_temperature = raw["llm_temperature"]
    if "llm_model" in raw:
        config.llm_model = raw["llm_model"]
    return config


def _parse_report(raw: dict) -> ReportConfig:
    """Parse raw YAML dict into ReportConfig."""
    config = ReportConfig()
    if "template_path" in raw:
        config.template_path = raw["template_path"]
    if "output_format" in raw:
        config.output_format = raw["output_format"]
    if "include_charts" in raw:
        config.include_charts = raw["include_charts"]
    if "max_quotes_per_category" in raw:
        config.max_quotes_per_category = raw["max_quotes_per_category"]
    return config


def load_config(config_dir: str | Path = "./config") -> AppConfig:
    """Load all configuration files and environment variables.

    Args:
        config_dir: Path to the config directory containing YAML files.

    Returns:
        Fully populated AppConfig instance.
    """
    # Load .env file if present
    load_dotenv()

    config_path = Path(config_dir)

    # Load YAML configs
    sources_raw = _load_yaml(config_path / "sources.yaml")
    analysis_raw = _load_yaml(config_path / "analysis.yaml")
    report_raw = _load_yaml(config_path / "report.yaml")

    # Build typed config
    app_config = AppConfig(
        sources=_parse_sources(sources_raw),
        analysis=_parse_analysis(analysis_raw),
        report=_parse_report(report_raw),
        data_dir=os.getenv("DATA_DIR", "./data"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
    )

    return app_config
