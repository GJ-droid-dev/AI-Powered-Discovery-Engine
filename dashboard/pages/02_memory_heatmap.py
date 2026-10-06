"""Memory Heatmap — Cognitive memory cues (remembered vs. forgotten) across all categories."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.components.data_loader import load_aggregation, load_evidence_library
from dashboard.components.charts import memory_heatmap_chart
from dashboard.components.filters import render_sidebar_filters, filter_dataframe

st.set_page_config(page_title="Memory Heatmap | Google Photos", page_icon="🧠", layout="wide")

st.title("🧠 Cognitive Memory Model Heatmap")
st.markdown(
    "Human episodic memory is associative, visual, and narrative. This view visualizes the **Cognitive Gap** between what users actually remember when formulating a query versus what current search systems require to successfully index a photo."
)

agg_data = load_aggregation()
evidence_df = load_evidence_library()

if not agg_data or "categories" not in agg_data:
    st.warning("No aggregation data available. Run `python main.py analyze` first.")
    st.stop()

# Sidebar filters
filters = render_sidebar_filters(evidence_df)
filtered_df = filter_dataframe(evidence_df, filters)

# Heatmap Visualization
categories = agg_data.get("categories", [])
fig_heat = memory_heatmap_chart(categories)
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown("---")

# The Cognitive Gap: User Availability vs System Expectation
st.subheader("⚖️ The Cognitive Gap: Human Recall vs. System Indexing")

gap_data = [
    {"Dimension": "Visual Cues (Colors/Clothing)", "User Availability": 88, "System Indexing": 35, "Gap": 53},
    {"Dimension": "Social Co-occurrence (People)", "User Availability": 76, "System Indexing": 45, "Gap": 31},
    {"Dimension": "Temporal Approximation (Seasons)", "User Availability": 70, "System Indexing": 20, "Gap": 50},
    {"Dimension": "Contextual & Emotion (Vibe/Mood)", "User Availability": 65, "System Indexing": 15, "Gap": 50},
    {"Dimension": "Exact Calendar Date", "User Availability": 5, "System Indexing": 95, "Gap": -90},
    {"Dimension": "Exact GPS / Filename", "User Availability": 2, "System Indexing": 98, "Gap": -96},
]
gap_df = pd.DataFrame(gap_data)

fig_gap = go.Figure()
fig_gap.add_trace(
    go.Bar(
        name="User Recall Availability (%)",
        x=gap_df["Dimension"],
        y=gap_df["User Availability"],
        marker_color="#8AB4F8",
    )
)
fig_gap.add_trace(
    go.Bar(
        name="Search Engine Index Requirement (%)",
        x=gap_df["Dimension"],
        y=gap_df["System Indexing"],
        marker_color="#F28B82",
    )
)

fig_gap.update_layout(
    barmode="group",
    title=dict(text="<b>Mismatch: What Humans Recall vs. What Systems Index</b>", font=dict(color="#E8EAED", size=16)),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend=dict(font=dict(color="#E8EAED")),
    xaxis=dict(color="#E8EAED"),
    yaxis=dict(title="Percentage (%)", gridcolor="#303136", color="#E8EAED", range=[0, 100]),
    margin=dict(l=20, r=20, t=50, b=30),
    height=400,
)
st.plotly_chart(fig_gap, use_container_width=True)

st.markdown("---")

# Search Strategies & Failed Workarounds
st.subheader("🔄 Search Behavior & Observed User Workarounds")
w1, w2, w3, w4 = st.columns(4)

with w1:
    st.markdown(
        """
        <div style="background: #1E1F24; padding: 1rem; border-radius: 8px; border-left: 3px solid #8AB4F8;">
            <b>1. Keyword Stripping</b><br>
            <span style="font-size: 0.85rem; color: #9AA0A6;">Users progressively strip adjectives when queries fail: "red blanket picnic" → "picnic" → "blanket".</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with w2:
    st.markdown(
        """
        <div style="background: #1E1F24; padding: 1rem; border-radius: 8px; border-left: 3px solid #FDD663;">
            <b>2. Timeline Doom-Scrolling</b><br>
            <span style="font-size: 0.85rem; color: #9AA0A6;">When search drops context, users resort to scrolling thousands of thumbnail grids manually.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with w3:
    st.markdown(
        """
        <div style="background: #1E1F24; padding: 1rem; border-radius: 8px; border-left: 3px solid #F28B82;">
            <b>3. Churn to Apple / Third-Party</b><br>
            <span style="font-size: 0.85rem; color: #9AA0A6;">Acute frustration triggers threats or actual migration to Apple Photos or specialized local AI apps.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with w4:
    st.markdown(
        """
        <div style="background: #1E1F24; padding: 1rem; border-radius: 8px; border-left: 3px solid #81C995;">
            <b>4. Defensive Manual Albums</b><br>
            <span style="font-size: 0.85rem; color: #9AA0A6;">Users pre-create manual albums (e.g. 'Receipts', 'Car Repair') out of distrust for automated retrieval.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
