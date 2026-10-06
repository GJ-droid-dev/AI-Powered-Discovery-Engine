"""Evidence Search — Searchable index of all user feedback, quotes, and cognitive memory models."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from dashboard.components.data_loader import load_evidence_library
from dashboard.components.filters import render_sidebar_filters, filter_dataframe

st.set_page_config(page_title="Evidence Search | Google Photos", page_icon="🔍", layout="wide")

st.title("🔍 Grounded Evidence Library & Search")
st.markdown(
    "Search across the entire catalog of **98 empirically analyzed user complaints**. Every insight, taxonomy category, and opportunity ranking in this project traces directly back to these primary sources."
)

evidence_df = load_evidence_library()

if evidence_df.empty:
    st.warning("No evidence library found. Run `python main.py analyze` first.")
    st.stop()

# Sidebar filters
filters = render_sidebar_filters(evidence_df)
filtered_df = filter_dataframe(evidence_df, filters)

# Keyword search input
col_search, col_sort = st.columns([3, 1])
with col_search:
    search_term = st.text_input("🔎 Search quotes, failure modes, or cognitive cues:", placeholder="e.g. 'wedding', 'yellow suitcase', 'receipt', 'Gemini'").strip().lower()

with col_sort:
    sort_by = st.selectbox("Sort By:", ["Severity (High to Low)", "Severity (Low to High)", "Category"])

# Apply search filter
if search_term:
    mask = (
        filtered_df["text"].str.lower().str.contains(search_term, na=False)
        | filtered_df["failure_description"].str.lower().str.contains(search_term, na=False)
        | filtered_df["remembered_summary"].str.lower().str.contains(search_term, na=False)
        | filtered_df["keywords_tried"].str.lower().str.contains(search_term, na=False)
    )
    filtered_df = filtered_df[mask]

# Sorting
if sort_by == "Severity (High to Low)":
    filtered_df = filtered_df.sort_values(by="severity_score", ascending=False)
elif sort_by == "Severity (Low to High)":
    filtered_df = filtered_df.sort_values(by="severity_score", ascending=True)
elif sort_by == "Category":
    filtered_df = filtered_df.sort_values(by="category_primary")

st.markdown(f"**Found {len(filtered_df)} matching evidence entries** (out of {len(evidence_df)} total)")

# Export button
csv_exp = filtered_df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Export Matching Evidence to CSV",
    data=csv_exp,
    file_name="evidence_library_filtered.csv",
    mime="text/csv",
)

st.write("")

# Render Evidence Cards
for _, row in filtered_df.iterrows():
    sev = float(row.get("severity_score", 0))
    sev_badge = "#F28B82" if sev > 50 else ("#FDD663" if sev > 30 else "#81C995")
    rating = row.get("rating")
    rating_str = f"{'★' * int(rating)}{'☆' * (5 - int(rating))}" if (rating and rating != "N/A" and str(rating).isdigit()) else ""

    with st.container():
        st.markdown(
            f"""
            <div style="background: #1E1F24; border: 1px solid #303136; border-radius: 10px; padding: 1.2rem; margin-bottom: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                    <div>
                        <span style="font-weight: bold; color: #8AB4F8; font-size: 1.05rem;">{str(row.get('category_primary')).replace('_', ' ').title()}</span>
                        <span style="margin-left: 0.8rem; background: #303136; color: #BDC1C6; padding: 2px 8px; border-radius: 4px; font-size: 0.8rem;">{str(row.get('source_type')).upper()}</span>
                        <span style="margin-left: 0.6rem; color: #FDD663; font-size: 0.9rem;">{rating_str}</span>
                    </div>
                    <div>
                        <span style="background: {sev_badge}; color: #000; padding: 3px 10px; border-radius: 12px; font-size: 0.85rem; font-weight: bold;">Severity: {sev:.1f}/100</span>
                    </div>
                </div>
                <div style="font-style: italic; color: #E8EAED; font-size: 0.95rem; margin-bottom: 0.8rem; line-height: 1.4;">
                    "{row.get('text', '')}"
                </div>
                <div style="background: #121316; border-radius: 6px; padding: 0.6rem; margin-bottom: 0.6rem; font-size: 0.85rem;">
                    <div style="color: #9AA0A6;"><b>Failure Diagnosis:</b> <span style="color: #E8EAED;">{row.get('failure_description', 'N/A')}</span></div>
                    {f'<div style="color: #8AB4F8; margin-top: 0.3rem;"><b>Remembered Cues:</b> {row.get("remembered_summary")}</div>' if row.get("remembered_summary") else ''}
                    {f'<div style="color: #F28B82; margin-top: 0.2rem;"><b>Forgotten / Missing:</b> {row.get("forgotten_summary")}</div>' if row.get("forgotten_summary") else ''}
                    {f'<div style="color: #FDD663; margin-top: 0.2rem;"><b>Keywords Attempted:</b> {row.get("keywords_tried")}</div>' if row.get("keywords_tried") else ''}
                </div>
                {f'<div><a href="{row.get("source_url")}" target="_blank" style="color: #8AB4F8; font-size: 0.8rem; text-decoration: none;">🔗 Open Source Attribution Reference</a></div>' if row.get("source_url") else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )
