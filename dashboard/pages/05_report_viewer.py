"""Report Viewer — Executive Discovery Report and Artifact Downloads."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from dashboard.components.data_loader import load_report_markdown

st.set_page_config(page_title="Executive Report | Google Photos", page_icon="📑", layout="wide")

st.title("📑 Executive Discovery Report")
st.markdown(
    "Full synthesis report generated for product leadership, outlining the problem diagnosis, grounded taxonomy, cognitive memory model, opportunity rankings, and 12-month engineering roadmap."
)

report_md = load_report_markdown()

# Download buttons row
col_d1, col_d2, col_d3 = st.columns(3)
with col_d1:
    st.download_button(
        label="📥 Download Full Report (Markdown)",
        data=report_md,
        file_name="google_photos_discovery_report.md",
        mime="text/markdown",
    )

with col_d2:
    csv_path = ROOT_DIR / "data" / "outputs" / "evidence_library.csv"
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            csv_data = f.read()
        st.download_button(
            label="📥 Download Evidence Library (CSV)",
            data=csv_data,
            file_name="evidence_library.csv",
            mime="text/csv",
        )

with col_d3:
    json_path = ROOT_DIR / "data" / "processed" / "aggregation.json"
    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = f.read()
        st.download_button(
            label="📥 Download Aggregation Data (JSON)",
            data=json_data,
            file_name="aggregation.json",
            mime="application/json",
        )

st.markdown("---")

# Render Markdown report
st.markdown(report_md)
