"""Data-backed start page for the DT-CARGO analyst workspace."""

from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st

from src.webapp.data import (
    DISPLAY_CLUSTER_LABELS,
    DISPLAY_CLUSTER_NAMES,
    load_cluster_assignments,
    load_overview_data,
)
from src.webapp.navigation import get_page_link
from src.webapp.three_motion import render_3d_fleet_canvas


ROUTE_GROUPS = [
    (
        "Operations HQ",
        "Start with fleet activity, then narrow the view to a vehicle, track, or review signal.",
        [
            ("Fleet Overview", "See recorded activity, distance, and utilization summaries.", "Open fleet overview", "card-fleet-overview.png", "Realistic freight fleet arranged at a dispatch yard"),
            ("Anomaly Monitoring", "Review records the model marked for a closer look.", "Open review queue", "card-anomaly-monitoring.png", "A freight truck highlighted by an amber telemetry spike"),
            ("Vehicle Explorer", "Follow one vehicle’s tracks, patterns, and review history.", "Explore vehicles", "card-vehicle-explorer.png", "A single blue freight truck on an inspection platform"),
            ("Track Explorer", "Inspect a recorded trip, its speed, stops, and data quality.", "Explore tracks", "card-track-explorer.png", "A truck following an illustrative route with waypoints"),
        ],
    ),
    (
        "Plan & simulate",
        "Plan a hypothetical tour, then replay a real recorded trip and its measured speed trace.",
        [
            ("Tour Duration Prediction", "Estimate tour time using information known before departure.", "Estimate tour duration", "card-tour-prediction.png", "A freight truck before departure with a projected route and time dial"),
            ("3D Speed Simulator", "Replay measured speed from a real saved trip in a schematic 3D road scene.", "Replay a recorded trip", "card-speed-simulator.png", "A truck on a schematic road, representing recorded speed replay"),
        ],
    ),
    (
        "The data room",
        "Learn what the saved groups mean, how complete the records are, and how each model works.",
        [
            ("Project & Dataset", "See the dataset scope, collection period, and what it can support.", "Read the project overview", "card-project-dataset.png", "Freight truck beside layers of trip-record tiles"),
            ("Cluster Analysis", "See how the two saved groups differ in distance, elapsed time, and episode count.", "Compare movement patterns", "card-cluster-analysis.png", "Illustrative freight trucks marked with the two movement-group colors"),
            ("Data Distribution", "See how the recorded values are spread across the fleet.", "Explore data distributions", "card-data-distribution.png", "A freight truck beside a three-dimensional distribution chart"),
            ("Data Quality", "Check missing, inconsistent, and model-ineligible records.", "Review data quality", "card-data-quality.png", "Truck telemetry sensors with verified and incomplete signal markers"),
            ("Model Insights", "Understand the methods, validation results, and limitations.", "Read model insights", "card-model-insights.png", "Three stages showing anomaly review, clustering, and duration prediction"),
        ],
    ),
]


def _read_fleet_summary() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]] | None:
    loaded = load_overview_data()
    if loaded is None:
        return None

    tracks, anomalies = loaded
    tracks = tracks.dropna(subset=["start_time"]).copy()
    if tracks.empty:
        return tracks, anomalies, {}

    distance = pd.to_numeric(tracks["distance_km"], errors="coerce").clip(lower=0)
    summary: dict[str, object] = {
        "vehicles": int(tracks["vehicle_id"].nunique(dropna=True)),
        "tracks": int(tracks["track_id"].nunique(dropna=True)),
        "fleet_groups": int(tracks["fleet_test_id"].nunique(dropna=True)),
        "tours": int(tracks["tour_id"].nunique(dropna=True)),
        "distance_km": float(distance.sum(skipna=True)),
        "first_day": tracks["start_time"].min().date(),
        "last_day": tracks["start_time"].max().date(),
    }
    if not anomalies.empty and "is_anomaly" in anomalies:
        flagged = anomalies.loc[anomalies["is_anomaly"]]
        summary["flagged"] = int(flagged["track_id"].nunique(dropna=True))
        summary["scored_tracks"] = int(anomalies["track_id"].nunique(dropna=True))
    else:
        summary["flagged"] = None
        summary["scored_tracks"] = None
    return tracks, anomalies, summary


CARD_TAGS = {
    "Fleet Overview": "FLEET STATUS",
    "Anomaly Monitoring": "ANOMALY REVIEW",
    "Vehicle Explorer": "VEHICLE PROFILE",
    "Track Explorer": "RECORDED TRACK",
    "Tour Duration Prediction": "PRE-TRIP ESTIMATE",
    "3D Speed Simulator": "DRIVE SIMULATION",
    "Project & Dataset": "DATASET SCOPE",
    "Cluster Analysis": "MOVEMENT GROUPS",
    "Data Distribution": "DATA SPREAD",
    "Data Quality": "QUALITY CHECKS",
    "Model Insights": "MODEL METHODS",
}


def _page_card(title: str, description: str, action: str, image: str, image_alt: str) -> None:
    page = get_page_link(title)
    with st.container(key=f"home-card-{title.lower().replace(' ', '-')}"):
        st.markdown(
            f"<div class='home-card-image'><img src='/app/static/{image}' "
            f"alt='{image_alt}' loading='lazy' decoding='async'>"
            f"<span class='home-card-kicker'>{CARD_TAGS.get(title, 'FLEET INTEL')}</span>"
            "<span class='home-card-badge'>ILLUSTRATIVE</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {title}")
        st.write(description)
        if page is not None:
            st.page_link(page, label=action, icon=":material/arrow_forward:")
        else:
            st.caption("This page is not registered yet.")


def render_home() -> None:
    """Render the approachable, data-backed entry point for all analysis pages."""
    loaded = _read_fleet_summary()
    summary = loaded[2] if loaded is not None else {}

    with st.container(key="home-hero"):
        st.caption("OPERATIONS HQ  /  HISTORICAL VEHICLE TELEMETRY")
        st.title("The road ahead, seen clearly.")
        st.write(
            "Explore recorded movement, investigate unusual trips, and estimate tour time "
            "with explanations that make sense without a data science background."
        )
        actions = st.columns(2, gap="small")
        overview_page = get_page_link("Fleet Overview")
        anomaly_page = get_page_link("Anomaly Monitoring")
        if overview_page is not None:
            actions[0].page_link(overview_page, label="View fleet activity", icon=":material/arrow_forward:")
        if anomaly_page is not None:
            actions[1].page_link(anomaly_page, label="Review unusual trips", icon=":material/search:")
        if summary:
            st.caption(
                f"Recorded data · {summary['first_day']:%b %Y} to {summary['last_day']:%b %Y}"
            )
        else:
            st.caption("Historical vehicle telemetry · GPS coordinates are not available in this dataset.")

    with st.container(key="home-workflow"):
        st.markdown("## What this ML project helps you understand")
        st.caption(
            "Three useful answers from the saved DT-CARGO telemetry, explained in everyday language."
        )
        workflow = [
            ("patterns", "01 · MOVEMENT GROUPS", "Understand trip patterns", "Compare longer-distance travel with low movement and long gaps. These groups describe recorded trips, not driver performance.", "Cluster Analysis", "Explore the two groups"),
            ("review", "02 · ANOMALY REVIEW", "Find unusual trips", "See which records differ from common patterns and what drove the review score. A flag is a prompt to look closer, not proof of an incident.", "Anomaly Monitoring", "Review unusual trips"),
            ("duration", "03 · TOUR DURATION", "Estimate tour time", "Enter vehicle details, planned distance, and departure timing to get a planning estimate with its known limits.", "Tour Duration Prediction", "Estimate tour duration"),
        ]
        workflow_columns = st.columns(3, gap="medium")
        for column, item in zip(workflow_columns, workflow):
            key, eyebrow, title, detail, destination, action = item
            with column:
                with st.container(key=f"home-step-{key}"):
                    st.markdown(f"<span class='home-step-kicker'>{eyebrow}</span>", unsafe_allow_html=True)
                    st.markdown(f"#### {title}")
                    st.write(detail)
                    page = get_page_link(destination)
                    if page is not None:
                        st.page_link(page, label=action, icon=":material/arrow_forward:")
        st.caption(
            "Historical DT-CARGO records only · no live GPS location, fuel, or vehicle-health feed is available here."
        )

    st.markdown("## A clear picture of the recorded fleet")
    if loaded is None:
        st.info(
            "Fleet totals will appear when the processed track dataset is available. "
            "You can still open any analysis page below."
        )
    elif not summary:
        st.info("The processed dataset is present, but it has no records with a valid start time.")
    else:
        st.caption(
            f"{summary['first_day']:%d %b %Y} – {summary['last_day']:%d %b %Y}"
            " · totals reflect the available processed records"
        )
        with st.container(key="home-metrics"):
            cards = [
                ("Tracks", f"{summary['tracks']:,}"),
                ("Vehicles", f"{summary['vehicles']:,}"),
                ("Fleets", f"{summary['fleet_groups']:,}"),
                ("Distance", f"{summary['distance_km']:,.0f} km"),
            ]
            card_html = "".join(
                f"<article class='home-kpi' role='group' aria-label='{label}: {value}'>"
                f"<span>{label}</span><strong>{value}</strong></article>"
                for label, value in cards
            )
            st.markdown(f"<div class='home-kpi-grid'>{card_html}</div>", unsafe_allow_html=True)

        cluster_assignments = load_cluster_assignments()
        if summary.get("flagged") is None:
            flagged_count = "Not available"
            signal_copy = "Saved anomaly validation results are not available in this workspace."
        else:
            flagged_count = f"{summary['flagged']:,}"
            signal_copy = (
                f"From {summary['scored_tracks']:,} scored validation tracks. "
                "These are prompts to review, not confirmed incidents or a live alert count."
            )

        if cluster_assignments is None or cluster_assignments.empty:
            pattern_content = "<p>Saved episode assignments are not available for this workspace.</p>"
        else:
            counts = (
                cluster_assignments.groupby("cluster", dropna=True)
                .size()
                .reindex([0, 1], fill_value=0)
            )
            total = int(counts.sum())
            pattern_rows = []
            for cluster in (0, 1):
                value = int(counts.loc[cluster])
                share = (value / max(total, 1)) * 100
                pattern_rows.append(
                    f"<div class='home-pattern-row' role='group' aria-label='{escape(DISPLAY_CLUSTER_LABELS[cluster])}: {value:,} saved episodes'>"
                    f"<div class='home-pattern-heading'><strong>{escape(DISPLAY_CLUSTER_NAMES[cluster])}</strong>"
                    f"<span>Cluster {cluster} · {value:,} saved episodes</span></div>"
                    f"<div class='home-pattern-track' aria-hidden='true'>"
                    f"<span class='home-pattern-fill home-pattern-fill-{cluster}' style='width:{share:.1f}%'></span></div></div>"
                )
            pattern_content = "".join(pattern_rows)

        with st.container(key="home-insights"):
            st.markdown(
                f"""
                <section class="home-insight-grid" aria-label="Operational signals and movement patterns">
                  <article class="home-insight-card" aria-label="Review signals: {flagged_count} validation candidates">
                    <span class="home-insight-kicker">MODEL REVIEW</span>
                    <h3>Review signals</h3>
                    <strong class="home-insight-value">{flagged_count}</strong>
                    <p>{signal_copy}</p>
                    <a class="home-insight-action" href="/anomaly-monitoring">See flagged records <span aria-hidden="true">→</span></a>
                  </article>
                  <article class="home-insight-card" aria-label="Two saved movement patterns">
                    <span class="home-insight-kicker">SAVED MOVEMENT GROUPS</span>
                    <h3>Two movement patterns</h3>
                    {pattern_content}
                    <p class="home-insight-note">Names describe movement only; they are not fault or driver ratings.</p>
                    <a class="home-insight-action" href="/cluster-analysis">Learn what the groups mean <span aria-hidden="true">→</span></a>
                  </article>
                </section>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("## Choose where to go next")
    st.write("Every page has a plain-language explanation alongside its charts and records.")
    for index, (group_title, description, cards) in enumerate(ROUTE_GROUPS):
        with st.container(key=f"home-routes-{index}"):
            st.markdown(f"### {group_title}")
            st.write(description)
            for offset in range(0, len(cards), 2):
                columns = st.columns(2, gap="medium")
                for column, card in zip(columns, cards[offset : offset + 2]):
                    with column:
                        _page_card(*card)

    with st.container(key="home-model-stage"):
        st.markdown("## Take a closer look")
        st.write("Drag or swipe to rotate the 3D truck. The view buttons and arrow keys work as alternatives.")
        render_3d_fleet_canvas(
            active_vehicles=int(summary.get("vehicles", 0)),
            tracks_count=int(summary.get("tracks", 0)),
            recorded_km=float(summary.get("distance_km", 0.0)),
            height=390,
        )
        st.caption("Illustrative model only · the available records do not include GPS coordinates or live vehicle positions.")

    st.caption(
        "Dataset boundary: the saved telemetry contains vehicle and trip records, but no latitude or longitude. "
        "Route scenes are illustrative; predictions use only features available before a tour starts."
    )
