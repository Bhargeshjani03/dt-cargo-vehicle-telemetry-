"""Apple-inspired, scroll-led summary of the selected fleet window."""

from __future__ import annotations

from html import escape
from textwrap import dedent

import pandas as pd
import streamlit as st

from src.webapp.data import DISPLAY_CLUSTER_NAMES


def _sparkline_points(monthly_counts: pd.DataFrame) -> tuple[str, str, float, float]:
    values = pd.to_numeric(monthly_counts.get("tracks", pd.Series(dtype=float)), errors="coerce")
    values = values.fillna(0).tolist()
    if not values:
        return "", "", 608.0, 156.0

    top, baseline = 16.0, 156.0
    maximum = max(max(values), 1)
    points = []
    for index, value in enumerate(values):
        x = 12.0 + (596.0 * index / max(len(values) - 1, 1))
        y = baseline - (value / maximum * (baseline - top))
        points.append((x, y))

    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = (
        f"12,{baseline:.1f} "
        + line.replace(" ", " ")
        + f" 608,{baseline:.1f}"
    )
    return line, area, points[-1][0], points[-1][1]


def render_scroll_story(
    *,
    fleet_label: str,
    date_label: str,
    track_count: int,
    vehicle_count: int,
    distance_km: float,
    monthly_counts: pd.DataFrame,
    cluster_counts: pd.DataFrame,
    flagged_count: int | None,
) -> None:
    """Render a sticky fleet signal with scroll-revealed, data-backed chapters."""
    line_points, area_points, last_x, last_y = _sparkline_points(monthly_counts)
    months = len(monthly_counts)
    range_label = escape(f"{fleet_label} · {date_label}")
    month_range = (
        f"{monthly_counts['month'].iloc[0]} – {monthly_counts['month'].iloc[-1]}"
        if months and "month" in monthly_counts
        else "No monthly activity"
    )
    distance_label = f"{distance_km:,.0f} km"
    validation_label = f"{flagged_count:,}" if flagged_count is not None else "Not available"

    counts = {cluster: 0 for cluster in (0, 1)}
    if not cluster_counts.empty:
        for row in cluster_counts.itertuples(index=False):
            try:
                cluster = int(row.cluster)
                if cluster in counts:
                    counts[cluster] = int(row.episodes)
            except (TypeError, ValueError):
                continue
    episode_total = sum(counts.values())
    max_cluster_count = max(max(counts.values()), 1)
    cluster_rows = "".join(
        "<div class='story-cluster-row'>"
        f"<div class='story-cluster-label'><span>{DISPLAY_CLUSTER_NAMES[cluster]}</span><strong>{count:,}</strong></div>"
        "<div class='story-bar-track' aria-hidden='true'>"
        f"<span class='story-bar-fill' style='--share:{count / max_cluster_count:.4f}'></span>"
        "</div></div>"
        for cluster, count in counts.items()
    )
    cluster_summary = (
        f"{episode_total:,} saved 12-hour episodes match this selection: {counts[0]:,} longer-distance and {counts[1]:,} low-movement episodes. "
        "These are descriptive patterns, not fault labels."
        if not cluster_counts.empty
        else "Saved cluster assignments are unavailable for this selection, so no group sizes are shown."
    )
    if cluster_counts.empty:
        cluster_rows = "<p class='story-empty'>No matching cluster assignments</p>"
    visual = (
        f"<svg class='story-chart' viewBox='0 0 620 180' role='img' "
        f"aria-label='Monthly track activity across {escape(month_range)}'>"
        "<defs><linearGradient id='story-fill' x1='0' x2='0' y1='0' y2='1'>"
        "<stop offset='0%' stop-color='#8bd5b6' stop-opacity='.32'/>"
        "<stop offset='100%' stop-color='#8bd5b6' stop-opacity='0'/>"
        "</linearGradient></defs>"
        "<path class='story-gridline' d='M12 56H608 M12 106H608 M12 156H608'/>"
        + (f"<polygon class='story-chart-area' points='{area_points}'/>" if area_points else "")
        + (f"<polyline class='story-chart-line' points='{line_points}'/>" if line_points else "")
        + (f"<circle class='story-chart-dot' cx='{last_x:.1f}' cy='{last_y:.1f}' r='5'/>" if line_points else "")
        + "</svg>"
    )


    st.markdown(
        dedent(f"""
        <section class="fleet-scroll-story" aria-label="Fleet activity story">
          <div class="fleet-story-stage">
            <div class="story-stage-header">
              <span class="story-status"><i></i> FLEET SIGNAL</span>
              <span class="story-stage-range">{range_label}</span>
            </div>
            <div class="story-stage-core">
              <div class="story-stage-intro">
                <div class="story-stage-copy">
                  <p class="story-stage-kicker">TRACKS IN VIEW</p>
                  <p class="story-stage-value">{track_count:,}</p>
                  <p class="story-stage-support">Across {vehicle_count:,} vehicles in the selected records</p>
                </div>
              </div>
              {visual}
              <div class="story-chart-caption"><span>Monthly activity</span><span>{escape(month_range)}</span></div>
            </div>
            <div class="story-stage-footer">
              <span>Recorded distance</span><strong>{distance_label}</strong>
            </div>
          </div>
          <div class="fleet-story-chapters">
            <article class="story-chapter">
              <p class="story-chapter-index">01 <span>ACTIVITY</span></p>
              <h2>Start with the movement.</h2>
              <p>The selected window brings together {track_count:,} track records from {vehicle_count:,} vehicles. The line stays tied to your current fleet and date filters.</p>
              <div class="story-note">{range_label}</div>
            </article>
            <article class="story-chapter">
              <p class="story-chapter-index">02 <span>MOVEMENT PATTERNS</span></p>
              <h2>Two movement patterns.</h2>
              <p>{cluster_summary}</p>
              <div class="story-cluster-data">
                <div class="story-cluster-list" aria-label="Episode counts by movement group">{cluster_rows}</div>
              </div>
            </article>
            <article class="story-chapter">
              <p class="story-chapter-index">03 <span>ANALYST REVIEW</span></p>
              <h2>Signals invite a closer look.</h2>
              <p>Validation flags identify records for analyst review. A flag is not a diagnosis, and its score is not a probability.</p>
              <div class="story-review-callout">
                <strong>{validation_label}</strong>
                <span>tracks flagged in the saved validation set</span>
              </div>
            </article>
          </div>
        </section>
        """).strip(),
        unsafe_allow_html=True,
    )
