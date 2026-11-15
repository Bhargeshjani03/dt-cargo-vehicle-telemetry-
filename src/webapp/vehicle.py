"""Searchable, data-backed vehicle activity summary."""

import pandas as pd
import streamlit as st

from src.webapp.anomaly import load_anomaly_data
from src.webapp.data import attach_display_cluster_labels, load_track_records
from src.webapp.charts import render_horizontal_bars, render_line_chart, render_metric_grid


VEHICLE_COLUMNS = [
    "track_id", "vehicle_id", "tour_id", "start_time", "distance_km", "duration_minutes",
    "avg_speed_kmh", "gross_vehicle_weight", "total_mass_with_trailer", "axle_class", "fleet_test_id",
]


def render_vehicle_explorer() -> None:
    st.caption("INVESTIGATE")
    st.title("Vehicle Explorer")
    st.write("Find a vehicle and review its recorded activity, movement patterns, and saved review flags.")

    tracks = load_track_records(VEHICLE_COLUMNS)
    if tracks.empty:
        st.warning("Processed vehicle activity is not available in the current data folder.")
        return
    tracks["start_time"] = pd.to_datetime(tracks["start_time"], utc=True, errors="coerce")
    tracks = attach_display_cluster_labels(tracks)
    vehicles = sorted(pd.to_numeric(tracks["vehicle_id"], errors="coerce").dropna().astype(int).unique().tolist())
    query = st.text_input("Search vehicle ID", placeholder="For example, 56")
    matches = [vehicle for vehicle in vehicles if not query.strip() or query.strip() in str(vehicle)]
    if not matches:
        st.info("No vehicle IDs match that search.")
        return
    chosen = st.selectbox("Choose a vehicle", matches, format_func=lambda value: f"Vehicle {value}")
    vehicle_tracks = tracks.loc[pd.to_numeric(tracks["vehicle_id"], errors="coerce") == chosen].copy()
    if vehicle_tracks.empty:
        st.info("No processed tracks were found for this vehicle.")
        return

    anomalies = load_anomaly_data()
    vehicle_flags = pd.DataFrame()
    if anomalies is not None:
        anomaly_rows, _ = anomalies
        vehicle_flags = anomaly_rows.loc[
            (pd.to_numeric(anomaly_rows["vehicle_id"], errors="coerce") == chosen)
            & anomaly_rows["is_anomaly"]
        ].copy()

    distance = pd.to_numeric(vehicle_tracks["distance_km"], errors="coerce").clip(lower=0).sum()
    hours = pd.to_numeric(vehicle_tracks["duration_minutes"], errors="coerce").clip(lower=0).sum() / 60
    render_metric_grid([
        ("Recorded tracks", f"{len(vehicle_tracks):,}"),
        ("Recorded distance", f"{distance:,.0f} km"),
        ("Recorded time", f"{hours:,.1f} h"),
        ("Saved review flags", f"{len(vehicle_flags):,}"),
    ], label=f"Vehicle {chosen} summary")

    first = vehicle_tracks.sort_values("start_time").iloc[0]
    spec_items = []
    for label, field, unit in zip(
        ["Gross vehicle weight", "Total mass with trailer", "Axle class", "Fleet test group"],
        ["gross_vehicle_weight", "total_mass_with_trailer", "axle_class", "fleet_test_id"],
        [" kg", " kg", "", ""],
    ):
        value = first.get(field)
        spec_items.append((label, f"{float(value):,.0f}{unit}" if pd.notna(value) else "Not recorded"))
    render_metric_grid(spec_items, label="Vehicle specifications")

    monthly = (
        vehicle_tracks.dropna(subset=["start_time"])
        .assign(month=lambda frame: frame["start_time"].dt.strftime("%Y-%m"))
        .groupby("month", as_index=False)
        .agg(tracks=("track_id", "nunique"), distance_km=("distance_km", "sum"))
        .sort_values("month")
    )
    if not monthly.empty:
        st.subheader("Activity over time")
        render_line_chart(
            "Track records by month",
            "Higher points mean more track segments were recorded that month; they do not necessarily mean more completed deliveries.",
            monthly["month"].astype(str).tolist(),
            [{"label": "Tracks", "values": monthly["tracks"].tolist(), "color": "#63a9ff"}],
        )

    displayed_patterns = ["Cluster 0 · Longer-distance travel", "Cluster 1 · Low movement with long gaps"]
    pattern_counts = (
        vehicle_tracks.loc[vehicle_tracks["cluster_name"].isin(displayed_patterns)]
        .groupby("cluster_name").size().sort_values(ascending=False)
    )
    if not pattern_counts.empty:
        st.subheader("Tracks matched to movement patterns")
        render_horizontal_bars(
            "Matched tracks by pattern",
            "Individual tracks inherit the label of their saved 12-hour episode when a time match is available.",
            pattern_counts.index.tolist(), pattern_counts.values.tolist(),
            colors=["#63a9ff" if "Cluster 0" in label else "#ffc45e" for label in pattern_counts.index],
        )

    st.subheader("Recent activity")
    recent = vehicle_tracks.sort_values("start_time", ascending=False).head(100).copy()
    recent = recent.rename(columns={
        "track_id": "Track ID", "tour_id": "Tour ID", "start_time": "Start time (UTC)",
        "distance_km": "Distance (km)", "duration_minutes": "Duration (min)",
        "avg_speed_kmh": "Average speed (km/h)", "cluster_name": "Movement pattern",
    })
    table_columns = [
        "Track ID", "Tour ID", "Start time (UTC)", "Distance (km)",
        "Duration (min)", "Average speed (km/h)", "Movement pattern",
    ]
    st.dataframe(recent[[column for column in table_columns if column in recent]], hide_index=True, width="stretch")

    if not vehicle_flags.empty:
        st.subheader("Tracks saved for review")
        flagged = vehicle_flags.sort_values("anomaly_score", ascending=False).head(50)
        st.dataframe(
            flagged[["track_id", "start_time", "anomaly_score", "distance_km", "duration_minutes"]].rename(columns={
                "track_id": "Track ID", "start_time": "Start time (UTC)",
                "anomaly_score": "Unusualness score", "distance_km": "Distance (km)",
                "duration_minutes": "Duration (min)",
            }),
            hide_index=True, width="stretch",
        )
        st.caption("A saved review flag is a prompt to inspect the record, not a judgment about the vehicle.")
