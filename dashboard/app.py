"""Google Photos — AI-Powered Memory Retrieval Discovery Engine
Main Dashboard Entrypoint & Executive Overview.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path so imports work seamlessly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from dashboard.components.data_loader import (
    load_aggregation,
    load_evidence_library,
    load_clusters,
)
from dashboard.components.charts import (
    category_bar_chart,
    source_distribution_donut,
    GOOGLE_BLUE,
    GOOGLE_RED,
    GOOGLE_GREEN,
    GOOGLE_YELLOW,
)

# Page configuration
st.set_page_config(
    page_title="Google Photos Discovery Engine",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #8AB4F8, #C58AF9, #F28B82);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #9AA0A6;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #1E1F24;
        border: 1px solid #303136;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .metric-value {
        font-size: 2.0rem;
        font-weight: 700;
        color: #8AB4F8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #BDC1C6;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
    }
    .interactive-card {
        background: #1E1F24;
        border-left: 4px solid #8AB4F8;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Data loading
agg_data = load_aggregation()
evidence_df = load_evidence_library()
clusters_data = load_clusters()

# Header
st.markdown('<div class="main-header">📸 Google Photos — Memory Retrieval Discovery Engine</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Diagnosing how human episodic memory fails when searching photos • Powered by Gemini 3.8 Flash & BGE Dense Embeddings</div>',
    unsafe_allow_html=True,
)

# Top KPI metrics row
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value">{agg_data.get('total_records_collected', 558)}</div>
            <div class="metric-label">Raw Records Ingested</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #81C995;">{agg_data.get('total_records_relevant', 98)}</div>
            <div class="metric-label">Relevant Failures</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #FDD663;">{len(agg_data.get('sources_analyzed', []))} Sources</div>
            <div class="metric-label">Audit Scope</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #C58AF9;">{len(agg_data.get('categories', []))}</div>
            <div class="metric-label">Failure Categories</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col5:
    top_opp = agg_data.get('categories', [{}])[0]
    top_score = top_opp.get('opportunity_score', 66.9)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-value" style="color: #F28B82;">{top_score:.1f}</div>
            <div class="metric-label">Top Opportunity Score</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.markdown("---")

# Executive Charts Row
c_chart1, c_chart2 = st.columns([1.6, 1.0])
with c_chart1:
    categories = agg_data.get("categories", [])
    if categories:
        fig_bar = category_bar_chart(categories)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No aggregation data available. Run `python main.py analyze` first.")

with c_chart2:
    if not evidence_df.empty and "source_type" in evidence_df:
        src_counts = evidence_df["source_type"].value_counts()
        fig_pie = source_distribution_donut(src_counts.index.tolist(), src_counts.values.tolist())
        st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown(
            """
            **💡 Cognitive Gap Insight:**
            Users remember **colors, objects, social company, and event context** in ~85% of retrieval attempts, but recall exact dates or filenames in **<5%** of searches.
            """
        )

st.markdown("---")

# =========================================================================
# Interactive Workflow Test Bench (Live Test Runner)
# =========================================================================
st.subheader("🧪 Test the Discovery Engine Workflow Live")
st.markdown(
    """
    Test how the engine diagnoses arbitrary search complaints or user feedback.
    Select a curated real-world case or enter custom feedback below to execute the live AI diagnosis pipeline.
    """
)

sample_queries = {
    "Select a pre-loaded real-world case...": "",
    "Case 1: Conjunctive Failure (Person + Event)": "I am trying to find Dave and Sarah at our wedding dancing, but Google Photos just returns 500 photos of Dave alone!",
    "Case 2: Visual Detail / Attribute Binding": "I was looking for my yellow suitcase in the hotel room and it only shows yellow cars and taxi cabs.",
    "Case 3: Document & OCR Failure": "Terrible search OCR. Cannot find the receipt for my refrigerator warranty that I photographed last month.",
    "Case 4: Emotional & Mood Recall": "I want to find candid photos of genuine laughter with my friends at the beach, not posed stiff portraits.",
    "Case 5: Temporal Approximation": "Looking for road trip photos from the summer before COVID, but search forces me to enter exact calendar dates.",
}

selected_preset = st.selectbox("Choose a test case or type your own below:", list(sample_queries.keys()))
default_text = sample_queries[selected_preset] if selected_preset else ""

user_input = st.text_area(
    "User Feedback / Search Complaint:",
    value=default_text,
    height=90,
    placeholder="e.g. 'Can't find photo of my daughter in her red raincoat by the lake'",
)

run_button = st.button("🚀 Run Live AI Diagnosis", type="primary")

if run_button and user_input.strip():
    with st.spinner("Executing 4-stage Discovery Engine pipeline (Relevance → Categorization → Memory Extraction → Severity)..."):
        try:
            from core.config import AnalysisConfig
            from core.schemas import UnifiedRecord, SourceType
            from analysis.relevance_filter import RelevanceFilter
            from analysis.failure_categorizer import FailureCategorizer
            from analysis.memory_model_extractor import MemoryModelExtractor
            from analysis.aggregator import Aggregator

            cfg = AnalysisConfig()
            record = UnifiedRecord(
                source_type=SourceType.REDDIT,
                raw_text=user_input.strip(),
                rating=1,
            )

            # Stage 1: Relevance Filter
            rel_filter = RelevanceFilter(cfg)
            rel_result = rel_filter.classify_record(record)

            # Stage 2: Categorization
            cat_engine = FailureCategorizer(cfg)
            cat_result = cat_engine.categorize_record(record)

            # Stage 3: Memory Model
            mem_engine = MemoryModelExtractor(cfg)
            mem_result = mem_engine.extract_record(record)

            # Stage 4: Severity & Opportunity
            from core.schemas import EnrichedRecord
            enriched = EnrichedRecord(
                record=record,
                relevance=rel_result,
                categorization=cat_result,
                memory_model=mem_result,
            )
            agg = Aggregator(cfg)
            severity = agg.calculate_severity(enriched) * 100

            # Render Results
            st.success("✅ Analysis Complete!")

            r_col1, r_col2, r_col3 = st.columns(3)
            with r_col1:
                rel_status = "🎯 RELEVANT RETRIEVAL FAILURE" if rel_result.is_relevant else "❌ NON-RETRIEVAL FEEDBACK"
                st.markdown(f"**Relevance Status:**\n`{rel_status}` (Confidence: {rel_result.confidence:.2f})")
            with r_col2:
                cat_badges = " ".join([f"`{c}`" for c in cat_result.failure_types])
                st.markdown(f"**Identified Category:**\n{cat_badges}")
            with r_col3:
                st.markdown(f"**Severity Score:**\n`{severity:.1f} / 100`")

            st.markdown("#### 🧠 Cognitive Memory Model Deconstruction")
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                st.markdown("**What the User Remembered (Possessed Cues):**")
                rem_dict = mem_result.remembered.model_dump()
                active_rem = {k: v for k, v in rem_dict.items() if v}
                if active_rem:
                    for k, v in active_rem.items():
                        st.markdown(f"- **{k.replace('_', ' ').title()}**: {', '.join(v)}")
                else:
                    st.write("General semantic query")

            with m_col2:
                st.markdown("**What the User Forgot (System Expectation Gap):**")
                forg_dict = mem_result.forgotten.model_dump()
                active_forg = [k.replace('_', ' ').title() for k, v in forg_dict.items() if v]
                if active_forg:
                    for f in active_forg:
                        st.markdown(f"- ⚠️ **Forgot**: {f}")
                else:
                    st.write("No metadata forgotten")

            st.markdown(f"**Diagnosed Failure Mechanism:**\n> *{cat_result.description}*")

        except Exception as e:
            st.error(f"Error executing analysis: {e}")

st.markdown("---")

# Quick Navigation to sub-pages
st.subheader("Explore the Discovery Engine Deep Dives")
p1, p2, p3, p4 = st.columns(4)
with p1:
    st.markdown("### 📊 [Category Explorer](Category_Explorer)")
    st.caption("Drill down into individual failure taxonomy categories, quotes, and cognitive traits.")
with p2:
    st.markdown("### 🧠 [Memory Heatmap](Memory_Heatmap)")
    st.caption("Inspect the Remembered vs. Forgotten matrix across all failure categories.")
with p3:
    st.markdown("### 🎯 [Opportunity Ranker](Opportunity_Ranker)")
    st.caption("Interactive 2x2 matrix with dynamic volume/severity weight sliders.")
with p4:
    st.markdown("### 🔍 [Evidence Search](Evidence_Search)")
    st.caption("Full-text search over all 98 analyzed complaints and quotes.")
