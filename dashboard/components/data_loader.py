"""Data loader helper for Streamlit dashboard with caching."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent.parent.parent


@st.cache_data
def load_aggregation() -> dict[str, Any]:
    """Load aggregation metrics and category rankings."""
    path = BASE_DIR / "data" / "processed" / "aggregation.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_evidence_library() -> pd.DataFrame:
    """Load the full evidence library as a pandas DataFrame."""
    path = BASE_DIR / "data" / "outputs" / "evidence_library.json"
    if not path.exists():
        return pd.DataFrame()
    with open(path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return pd.DataFrame(entries)


@st.cache_data
def load_clusters() -> dict[str, Any]:
    """Load emergent clusters discovered via BGE embeddings."""
    path = BASE_DIR / "data" / "processed" / "clusters.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_analyzed_records() -> list[dict[str, Any]]:
    """Load detailed analyzed records."""
    path = BASE_DIR / "data" / "processed" / "analyzed.jsonl"
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


@st.cache_data
def load_report_markdown() -> str:
    """Load the executive markdown report."""
    path = BASE_DIR / "data" / "outputs" / "discovery_report.md"
    if not path.exists():
        return "Report not found. Run `python main.py report` first."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
