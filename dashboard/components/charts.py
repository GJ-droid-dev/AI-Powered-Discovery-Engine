"""Plotly chart builders styled for Google Photos Discovery Engine."""

from __future__ import annotations

from typing import Any
import plotly.express as px
import plotly.graph_objects as go


# Brand colors
GOOGLE_BLUE = "#8AB4F8"
GOOGLE_RED = "#F28B82"
GOOGLE_YELLOW = "#FDD663"
GOOGLE_GREEN = "#81C995"
GOOGLE_PURPLE = "#C58AF9"
BG_DARK = "#1E1F24"
TEXT_LIGHT = "#E8EAED"


def category_bar_chart(categories: list[dict[str, Any]]) -> go.Figure:
    """Horizontal bar chart showing opportunity scores and volume percentages."""
    cats = sorted(categories, key=lambda c: c.get("opportunity_score", 0), reverse=True)

    names = [c.get("category", "").replace("_", " ").title() for c in reversed(cats)]
    opp_scores = [c.get("opportunity_score", 0) for c in reversed(cats)]
    vol_counts = [c.get("volume_count", 0) for c in reversed(cats)]
    vol_pcts = [c.get("volume_percentage", 0) for c in reversed(cats)]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=names,
            x=opp_scores,
            orientation="h",
            marker=dict(
                color=opp_scores,
                colorscale="Blues",
                showscale=False,
                line=dict(color="#8AB4F8", width=1.5),
            ),
            text=[f"{s:.1f} pts ({v} complaints, {p}%)" for s, v, p in zip(opp_scores, vol_counts, vol_pcts)],
            textposition="inside",
            insidetextanchor="middle",
            hovertemplate="<b>%{y}</b><br>Opportunity Score: %{x:.1f}<br>Volume: %{text}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="<b>Opportunity Score by Failure Category</b>", font=dict(color=TEXT_LIGHT, size=18)),
        xaxis=dict(
            title="Opportunity Score (0-100)",
            gridcolor="#303136",
            color=TEXT_LIGHT,
            range=[0, 100],
        ),
        yaxis=dict(color=TEXT_LIGHT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=50, b=30),
        height=380,
    )
    return fig


def quadrant_scatter_chart(categories: list[dict[str, Any]]) -> go.Figure:
    """Severity vs Volume 2x2 Prioritization Quadrant chart."""
    x_vals = [c.get("volume_count", 0) for c in categories]
    y_vals = [c.get("severity_score", 0) for c in categories]
    text_labels = [c.get("category", "").replace("_", " ").title() for c in categories]
    opp_scores = [c.get("opportunity_score", 0) for c in categories]

    # Reference medians or means for quadrant lines
    x_mid = sum(x_vals) / len(x_vals) if x_vals else 15
    y_mid = sum(y_vals) / len(y_vals) if y_vals else 25

    fig = go.Figure()

    # Scatter points
    fig.add_trace(
        go.Scatter(
            x=x_vals,
            y=y_vals,
            mode="markers+text",
            text=text_labels,
            textposition="top center",
            textfont=dict(color=TEXT_LIGHT, size=12, family="sans serif"),
            marker=dict(
                size=[max(22, s * 0.55) for s in opp_scores],
                color=opp_scores,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Opportunity<br>Score", tickfont=dict(color=TEXT_LIGHT)),
                line=dict(color="#FFFFFF", width=1.5),
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "Volume: %{x} records<br>"
                + "Severity: %{y:.1f}/100<br>"
                + "<extra></extra>"
            ),
        )
    )

    # Quadrant dividing lines
    fig.add_vline(x=x_mid, line_dash="dash", line_color="#5F6368", line_width=1.5)
    fig.add_hline(y=y_mid, line_dash="dash", line_color="#5F6368", line_width=1.5)

    # Quadrant annotations
    max_x = max(x_vals) * 1.1 if x_vals else 50
    max_y = max(y_vals) * 1.15 if y_vals else 40

    fig.add_annotation(
        x=max_x * 0.85,
        y=max_y * 0.95,
        text="<b>HIGH VOLUME / HIGH SEVERITY<br>(Priority 1: Fix Now)</b>",
        showarrow=False,
        font=dict(color=GOOGLE_RED, size=11),
        align="center",
    )
    fig.add_annotation(
        x=x_mid * 0.35,
        y=max_y * 0.95,
        text="<b>LOW VOLUME / HIGH SEVERITY<br>(Niche Pain Points)</b>",
        showarrow=False,
        font=dict(color=GOOGLE_YELLOW, size=11),
        align="center",
    )
    fig.add_annotation(
        x=max_x * 0.85,
        y=y_mid * 0.35,
        text="<b>HIGH VOLUME / LOW SEVERITY<br>(Minor Frustrations)</b>",
        showarrow=False,
        font=dict(color=GOOGLE_BLUE, size=11),
        align="center",
    )
    fig.add_annotation(
        x=x_mid * 0.35,
        y=y_mid * 0.35,
        text="<b>LOW VOLUME / LOW SEVERITY<br>(Deprioritize)</b>",
        showarrow=False,
        font=dict(color="#9AA0A6", size=11),
        align="center",
    )

    fig.update_layout(
        title=dict(text="<b>Opportunity Matrix: Severity vs. Volume Quadrants</b>", font=dict(color=TEXT_LIGHT, size=18)),
        xaxis=dict(title="Volume (Complaint Count)", gridcolor="#303136", color=TEXT_LIGHT),
        yaxis=dict(title="Severity Score (0-100)", gridcolor="#303136", color=TEXT_LIGHT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=30, t=50, b=40),
        height=500,
    )
    return fig


def memory_heatmap_chart(categories: list[dict[str, Any]]) -> go.Figure:
    """Heatmap matrix comparing Remembered vs Forgotten attributes across categories."""
    attributes = [
        "visual_cues",
        "object_cues",
        "people",
        "event_context",
        "emotions",
        "exact_date (forgotten)",
        "exact_location (forgotten)",
        "file_name (forgotten)",
    ]

    cat_labels = [c.get("category", "").replace("_", " ").title() for c in categories]
    z_matrix: list[list[int]] = []

    for attr in attributes:
        row = []
        is_forgotten = "(forgotten)" in attr
        clean_attr = attr.replace(" (forgotten)", "").strip()

        for c in categories:
            if is_forgotten:
                freq = c.get("forgotten_frequency", {}).get(clean_attr, 0)
            else:
                freq = c.get("remembered_frequency", {}).get(clean_attr, 0)
            row.append(freq)
        z_matrix.append(row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=cat_labels,
            y=[a.replace("_", " ").title() for a in attributes],
            colorscale="Plasma",
            colorbar=dict(title="Mentions", tickfont=dict(color=TEXT_LIGHT)),
            hovertemplate="Category: <b>%{x}</b><br>Attribute: <b>%{y}</b><br>Mentions: %{z}<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(text="<b>Cognitive Memory Cues: Remembered vs. Forgotten by Category</b>", font=dict(color=TEXT_LIGHT, size=18)),
        xaxis=dict(color=TEXT_LIGHT, tickangle=-25),
        yaxis=dict(color=TEXT_LIGHT),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=50, r=30, t=50, b=60),
        height=480,
    )
    return fig


def source_distribution_donut(sources: list[str], counts: list[int]) -> go.Figure:
    """Donut chart for data source breakdown."""
    fig = go.Figure(
        data=[
            go.Pie(
                labels=[s.replace("_", " ").title() for s in sources],
                values=counts,
                hole=0.55,
                marker=dict(colors=[GOOGLE_BLUE, GOOGLE_RED, GOOGLE_YELLOW, GOOGLE_GREEN, GOOGLE_PURPLE]),
                textinfo="label+percent",
                hoverinfo="label+value+percent",
            )
        ]
    )
    fig.update_layout(
        title=dict(text="<b>Data Provenance by Source</b>", font=dict(color=TEXT_LIGHT, size=16)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
        height=280,
    )
    return fig
