"""Reusable sidebar filters for the Streamlit dashboard."""

from __future__ import annotations

from typing import Any
import pandas as pd
import streamlit as st


def render_sidebar_filters(df: pd.DataFrame) -> dict[str, Any]:
    """Render global sidebar filters and return selected filter values."""
    st.sidebar.title("🔍 Discovery Filters")
    st.sidebar.caption("Filter analyzed feedback across sources & categories")

    # Categories
    all_cats = sorted(df["category_primary"].dropna().unique().tolist()) if "category_primary" in df else []
    selected_cats = st.sidebar.multiselect(
        "Failure Category",
        options=all_cats,
        default=all_cats,
        format_func=lambda x: x.replace("_", " ").title(),
    )

    # Sources
    all_sources = sorted(df["source_type"].dropna().unique().tolist()) if "source_type" in df else []
    selected_sources = st.sidebar.multiselect(
        "Data Source",
        options=all_sources,
        default=all_sources,
        format_func=lambda x: x.replace("_", " ").title(),
    )

    # Severity Slider
    min_sev, max_sev = 0.0, 100.0
    if "severity_score" in df and not df.empty:
        min_sev = float(df["severity_score"].min())
        max_sev = float(df["severity_score"].max())

    sev_range = st.sidebar.slider(
        "Severity Score Range",
        min_value=0.0,
        max_value=100.0,
        value=(0.0, 100.0),
        step=5.0,
    )

    return {
        "categories": selected_cats,
        "sources": selected_sources,
        "min_severity": sev_range[0],
        "max_severity": sev_range[1],
    }


def filter_dataframe(df: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    """Filter evidence DataFrame using selected filters."""
    if df.empty:
        return df

    filtered = df.copy()

    if filters.get("categories"):
        filtered = filtered[filtered["category_primary"].isin(filters["categories"])]

    if filters.get("sources"):
        filtered = filtered[filtered["source_type"].isin(filters["sources"])]

    if "severity_score" in filtered:
        filtered = filtered[
            (filtered["severity_score"] >= filters["min_severity"])
            & (filtered["severity_score"] <= filters["max_severity"])
        ]

    return filtered
