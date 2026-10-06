"""Category Explorer — Deep dive into individual failure taxonomy categories."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from dashboard.components.data_loader import load_aggregation, load_clusters
from dashboard.components.charts import category_bar_chart

st.set_page_config(page_title="Category Explorer | Google Photos", page_icon="📊", layout="wide")

st.title("📊 Retrieval Failure Category Explorer")
st.markdown(
    "Explore the empirically grounded retrieval failure taxonomy. Each category represents a distinct breakdown between human memory recall and search engine indexing."
)

agg_data = load_aggregation()
categories = agg_data.get("categories", [])
clusters = load_clusters()

if not categories:
    st.warning("No aggregation data found. Please run `python main.py analyze` first.")
    st.stop()

# Category selector
cat_names = [c["category"] for c in categories]
cat_labels = {c: c.replace("_", " ").title() for c in cat_names}

selected_cat = st.selectbox(
    "Select Failure Category to Inspect:",
    cat_names,
    format_func=lambda x: f"{cat_labels[x]} (Opp Score: {next((c['opportunity_score'] for c in categories if c['category'] == x), 0):.1f})",
)

cat_data = next((c for c in categories if c["category"] == selected_cat), None)

if cat_data:
    # Top KPI Metrics for this category
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Opportunity Score", f"{cat_data['opportunity_score']:.1f} / 100")
    with col2:
        st.metric("Complaint Volume", f"{cat_data['volume_count']} records", f"{cat_data['volume_percentage']:.1f}% of failures")
    with col3:
        st.metric("Average Severity", f"{cat_data.get('severity_score', 0):.1f} / 100")
    with col4:
        st.metric("Feasibility Rating", "75 / 100")

    st.markdown("---")

    # Cognitive Memory Profile for this category
    st.subheader("🧠 Cognitive Memory Model Breakdown")
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        st.markdown("**What Users Possess (Remembered Cues):**")
        rem_freq = cat_data.get("remembered_frequency", {})
        if rem_freq:
            rem_df = [{"Attribute": k.replace("_", " ").title(), "Mentions": v} for k, v in rem_freq.items() if v > 0]
            if rem_df:
                fig_rem = px.bar(
                    rem_df,
                    x="Mentions",
                    y="Attribute",
                    orientation="h",
                    color="Mentions",
                    color_continuous_scale="Blues",
                )
                fig_rem.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E8EAED"),
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=220,
                )
                st.plotly_chart(fig_rem, use_container_width=True)
            else:
                st.info("No specific remembered attributes recorded.")
        else:
            st.info("No remembered attributes.")

    with m_col2:
        st.markdown("**What Users Forget (System Expectation Gap):**")
        forg_freq = cat_data.get("forgotten_frequency", {})
        if forg_freq:
            forg_df = [{"Attribute": k.replace("_", " ").title(), "Mentions": v} for k, v in forg_freq.items() if v > 0]
            if forg_df:
                fig_forg = px.bar(
                    forg_df,
                    x="Mentions",
                    y="Attribute",
                    orientation="h",
                    color="Mentions",
                    color_continuous_scale="Reds",
                )
                fig_forg.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E8EAED"),
                    margin=dict(l=20, r=20, t=20, b=20),
                    height=220,
                )
                st.plotly_chart(fig_forg, use_container_width=True)
            else:
                st.info("No specific forgotten attributes recorded.")
        else:
            st.info("No forgotten attributes.")

    st.markdown("---")

    # Emergent Cluster Information if applicable
    if selected_cat == "emergent" and clusters.get("clusters"):
        st.subheader("🧬 Emergent Cluster Discovery (BGE Dense Embeddings)")
        for cl in clusters["clusters"]:
            theme_title = cl.get("representative_theme", "Chronological & Date Search Override")
            cl_size = cl.get("size", len(cl.get("record_ids", [])))
            st.info(f"**Discovered Semantic Cluster #{cl.get('cluster_id', 1)}** ({cl_size} records)\n\n**Pattern Diagnosis:** {theme_title}")
            sample_quotes = cl.get("sample_quotes", [])
            if sample_quotes:
                st.markdown("**Sample Cluster Quotes:**")
                for sq in sample_quotes[:3]:
                    st.markdown(f"- *\"{sq}...\"*")

    # Top Representative Quotes
    st.subheader(f"💬 Top Representative Evidence Quotes ({len(cat_data.get('representative_quotes', []))} shown)")
    quotes = cat_data.get("representative_quotes", [])

    for idx, q in enumerate(quotes, 1):
        sev_val = float(q.get("severity_score", 0))
        sev_color = "#F28B82" if sev_val > 50 else ("#FDD663" if sev_val > 30 else "#81C995")

        with st.container():
            st.markdown(
                f"""
                <div style="background: #1E1F24; border: 1px solid #303136; border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span style="font-weight: bold; color: #8AB4F8;">Quote #{idx} • Source: {q.get('source_type', 'unknown').upper()}</span>
                        <span style="background: {sev_color}; color: #000; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">Severity: {sev_val:.1f}/100</span>
                    </div>
                    <div style="font-style: italic; color: #E8EAED; margin-bottom: 0.6rem;">"{q.get('text', '')}"</div>
                    <div style="font-size: 0.85rem; color: #9AA0A6;"><b>Failure Diagnosis:</b> {q.get('failure_description', 'N/A')}</div>
                    {f'<div style="margin-top: 0.4rem;"><a href="{q.get("source_url")}" target="_blank" style="color: #8AB4F8; font-size: 0.8rem;">🔗 View Source Attribution Link</a></div>' if q.get("source_url") else ''}
                </div>
                """,
                unsafe_allow_html=True,
            )
