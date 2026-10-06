"""Opportunity Ranker — Prioritization Matrix, 2x2 Quadrant Analysis, and Dynamic Weight Tuning."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd

from dashboard.components.data_loader import load_aggregation
from dashboard.components.charts import quadrant_scatter_chart

st.set_page_config(page_title="Opportunity Ranker | Google Photos", page_icon="🎯", layout="wide")

st.title("🎯 Opportunity Area Prioritization Matrix")
st.markdown(
    "Rank and prioritize discovery opportunities based on **complaint volume, frustration severity, and engineering feasibility**. Use the sliders in the sidebar to simulate different PM weighting strategies."
)

agg_data = load_aggregation()
categories = agg_data.get("categories", [])

if not categories:
    st.warning("No aggregation data available. Run `python main.py analyze` first.")
    st.stop()

# Sidebar Weight Sliders
st.sidebar.title("🎛️ Ranking Formula Weights")
st.sidebar.caption("Fine-tune the opportunity scoring equation:")
st.sidebar.latex(r"\text{Score} = w_{v} \cdot \text{Vol} + w_{s} \cdot \text{Sev} + w_{f} \cdot \text{Feas}")

w_vol = st.sidebar.slider("Volume Weight (w_v)", 0.0, 1.0, 0.40, 0.05)
w_sev = st.sidebar.slider("Severity Weight (w_s)", 0.0, 1.0, 0.40, 0.05)
w_feas = st.sidebar.slider("Feasibility Weight (w_f)", 0.0, 1.0, 0.20, 0.05)

# Normalize weights
total_w = w_vol + w_sev + w_feas
if total_w > 0:
    w_vol /= total_w
    w_sev /= total_w
    w_feas /= total_w

st.sidebar.info(f"Normalized: Vol {w_vol:.2f} | Sev {w_sev:.2f} | Feas {w_feas:.2f}")

# Feasibility defaults
FEASIBILITY_MAP = {
    "contextual_episodic": 70.0,
    "temporal_approximation": 85.0,
    "visual_detail": 75.0,
    "people_event": 80.0,
    "document_screenshot": 90.0,
    "object_in_scene": 80.0,
    "emotional_association": 65.0,
    "emergent": 75.0,
}

# Recompute dynamic opportunity scores
max_vol = max((c.get("volume_count", 1) for c in categories), default=1)

recalculated = []
for c in categories:
    cat_name = c.get("category", "")
    vol_cnt = c.get("volume_count", 0)
    vol_pct = c.get("volume_percentage", 0.0)
    sev_sc = c.get("severity_score", 0.0)
    feas = FEASIBILITY_MAP.get(cat_name, 75.0)

    vol_norm = (vol_cnt / max_vol) * 100
    dyn_opp = round((w_vol * vol_norm) + (w_sev * sev_sc) + (w_feas * feas), 2)

    # Quadrant tagging
    if vol_cnt >= 15 and sev_sc >= 22:
        quadrant = "🔴 Priority 1: Fix Now"
    elif vol_cnt < 15 and sev_sc >= 22:
        quadrant = "🟡 Priority 2: Niche Pain Point"
    elif vol_cnt >= 15 and sev_sc < 22:
        quadrant = "🔵 Priority 3: Minor Friction"
    else:
        quadrant = "⚪ Priority 4: Deprioritize"

    recalculated.append({
        "Category": cat_name.replace("_", " ").title(),
        "Volume Count": vol_cnt,
        "Volume %": f"{vol_pct:.1f}%",
        "Severity Score": f"{sev_sc:.1f}",
        "Feasibility": f"{feas:.0f}",
        "Opportunity Score": dyn_opp,
        "Strategic Priority": quadrant,
        "raw_category": cat_name,
        "raw_opp": dyn_opp,
        "raw_vol": vol_cnt,
        "raw_sev": sev_sc,
    })

# Sort by dynamic opportunity score descending
recalculated.sort(key=lambda x: x["raw_opp"], reverse=True)
for idx, r in enumerate(recalculated, 1):
    r["Rank"] = idx

# 2x2 Quadrant Chart
chart_cats = [
    {
        "category": r["raw_category"],
        "volume_count": r["raw_vol"],
        "severity_score": r["raw_sev"],
        "opportunity_score": r["raw_opp"],
    }
    for r in recalculated
]
fig_quad = quadrant_scatter_chart(chart_cats)
st.plotly_chart(fig_quad, use_container_width=True)

st.markdown("---")

# Ranking Leaderboard Table
st.subheader("📋 Opportunity Area Leaderboard")

display_cols = ["Rank", "Category", "Opportunity Score", "Volume Count", "Volume %", "Severity Score", "Feasibility", "Strategic Priority"]
df_display = pd.DataFrame(recalculated)[display_cols]

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
)

# Download CSV button
csv_data = df_display.to_csv(index=False).encode("utf-8")
st.download_button(
    label="📥 Download Opportunity Rankings CSV",
    data=csv_data,
    file_name="google_photos_opportunity_rankings.csv",
    mime="text/csv",
)
