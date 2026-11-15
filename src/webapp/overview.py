"""Fleet overview page — Apple design enhanced with 3D motion graphics."""

import pandas as pd
import streamlit as st

from src.webapp.charts import render_horizontal_bars, render_line_chart, render_metric_grid
from src.webapp.data import DISPLAY_CLUSTER_LABELS, DISPLAY_CLUSTER_NAMES, load_cluster_assignments, load_overview_data
from src.webapp.navigation import get_page_link
from src.webapp.scroll_story import render_scroll_story
from src.webapp.three_motion import render_3d_fleet_canvas


PERIOD_OPTIONS = ["All activity", "Last 12 months", "Last 90 days", "Custom"]


def render_overview() -> None:
    st.caption("FLEET ACTIVITY  ·  OPERATIONS")
    st.title("Fleet Overview")
    st.write("A clear, spatial view of recorded movement, telemetry intelligence, and signals worth a closer look.")

    data = load_overview_data()
    if data is None:
        st.info(
            "Fleet metrics appear when the processed track table is available. "
            "Expected file: `data/processed/engineered_tracks.csv`."
        )
        return

    tracks, anomalies = data
    tracks = tracks.dropna(subset=["start_time"]).copy()
    if tracks.empty:
        st.warning("The processed track table has no rows with a valid start time.")
        return

    first_day = tracks["start_time"].min().date()
    last_day = tracks["start_time"].max().date()
    fleet_groups = sorted(tracks["fleet_test_id"].dropna().unique().tolist())

    def reset_filters() -> None:
        st.session_state["overview_period"] = "All activity"
        st.session_state["overview_fleet_group"] = "All groups"
        st.session_state["overview_custom_range"] = (first_day, last_day)

    with st.container(key="overview-filters"):
        period_col, fleet_col, reset_col = st.columns([2, 1.2, 0.8])
        with period_col:
            period = st.selectbox(
                "Activity window",
                PERIOD_OPTIONS,
                key="overview_period",
            )
        with fleet_col:
            fleet_group = st.selectbox(
                "Fleet test group",
                options=["All groups", *fleet_groups],
                format_func=lambda value: str(value),
                key="overview_fleet_group",
            )
        with reset_col:
            st.button(
                "Reset",
                icon=":material/restart_alt:",
                on_click=reset_filters,
                help="Return to all activity and all groups.",
            )

    if period == "Custom":
        selected_range = st.date_input(
            "Custom date range",
            value=(first_day, last_day),
            min_value=first_day,
            max_value=last_day,
            key="overview_custom_range",
        )
        if isinstance(selected_range, (tuple, list)) and len(selected_range) == 2:
            start_day, end_day = selected_range
        elif isinstance(selected_range, (tuple, list)) and len(selected_range) == 1:
            start_day = end_day = selected_range[0]
        else:
            start_day = end_day = selected_range
    else:
        end_day = last_day
        if period == "Last 90 days":
            start_day = max(first_day, (pd.Timestamp(end_day) - pd.Timedelta(days=89)).date())
        elif period == "Last 12 months":
            start_day = max(first_day, (pd.Timestamp(end_day) - pd.Timedelta(days=364)).date())
        else:
            start_day = first_day

    start_utc = pd.Timestamp(start_day, tz="UTC")
    end_utc = pd.Timestamp(end_day, tz="UTC") + pd.Timedelta(days=1)
    filtered = tracks.loc[
        tracks["start_time"].ge(start_utc) & tracks["start_time"].lt(end_utc)
    ]
    if fleet_group != "All groups":
        filtered = filtered.loc[filtered["fleet_test_id"] == fleet_group]

    if filtered.empty:
        st.info("No track activity matches these filters. Widen the date range or choose another group.")
        return

    fleet_count = int(filtered["fleet_test_id"].nunique(dropna=True))
    vehicle_count = int(filtered["vehicle_id"].nunique(dropna=True))
    track_count = int(filtered["track_id"].nunique(dropna=True))
    distance_km = float(filtered["distance_km"].clip(lower=0).sum(skipna=True))
    fleet_label = "All groups" if fleet_group == "All groups" else f"Fleet test group {fleet_group}"

    with st.container(key="filter-summary"):
        st.markdown(
            f"**{fleet_label}**  ·  {start_day:%d %b %Y} – {end_day:%d %b %Y}  ·  "
            f"{track_count:,} tracks in view"
        )

    # ─────────────────────────── Apple-Inspired 3D Motion Graphics Stage ───────────────────────────
    st.subheader("Explore the truck model")
    st.caption("Drag or swipe to rotate; labeled controls also work with mouse, keyboard, and touch. The model is illustrative, not a live vehicle position.")
    render_3d_fleet_canvas(
        active_vehicles=vehicle_count,
        tracks_count=track_count,
        recorded_km=distance_km,
        height=440,
    )

    monthly = filtered.assign(month=filtered["start_time"].dt.strftime("%Y-%m"))
    monthly_counts = (
        monthly.groupby("month", as_index=False)
        .agg(tracks=("track_id", "nunique"))
        .sort_values("month")
    )

    assignments = load_cluster_assignments()
    if assignments is not None:
        assignments = assignments.loc[
            assignments["start_time"].ge(start_utc)
            & assignments["start_time"].lt(end_utc)
        ]
        selected_tours = filtered[["vehicle_id", "tour_id"]].dropna().drop_duplicates()
        assignments = assignments.merge(
            selected_tours,
            on=["vehicle_id", "tour_id"],
            how="inner",
        )
        cluster_counts = (
            assignments.groupby("cluster", as_index=False)
            .size()
            .rename(columns={"size": "episodes"})
            .sort_values("cluster")
        )
    else:
        cluster_counts = pd.DataFrame(columns=["cluster", "episodes"])

    flagged_count = None if anomalies.empty else int(
        anomalies.loc[anomalies["is_anomaly"], "track_id"].nunique()
    )
    render_scroll_story(
        fleet_label=fleet_label,
        date_label=f"{start_day:%d %b %Y} – {end_day:%d %b %Y}",
        track_count=track_count,
        vehicle_count=vehicle_count,
        distance_km=distance_km,
        monthly_counts=monthly_counts,
        cluster_counts=cluster_counts,
        flagged_count=flagged_count,
    )

    with st.container(key="kpi-grid"):
        render_metric_grid([
            ("Fleet groups", f"{fleet_count:,}"),
            ("Vehicles active", f"{vehicle_count:,}"),
            ("Tracks recorded", f"{track_count:,}"),
            ("Distance", f"{distance_km:,.0f} km"),
        ], label="Fleet summary")

    with st.expander("Explore the underlying activity data"):
        left, right = st.columns([1.55, 1])
        with left:
            st.subheader("Fleet activity over time")
            render_line_chart(
                "Recorded fleet activity",
                "Tracks started each month in the selected window. Focus or hover on a point for its exact count.",
                monthly_counts["month"].astype(str).tolist(),
                [{"label": "Tracks", "values": monthly_counts["tracks"].tolist(), "color": "#46d6a0"}],
            )
            st.dataframe(monthly_counts, hide_index=True, width="stretch")

        with right:
            st.subheader("Behavioral cluster mix")
            if assignments is None:
                st.caption("The saved episode assignments for source clusters 0 and 2 are not available.")
            elif cluster_counts.empty:
                st.caption("No saved cluster assignments match this selection.")
            else:
                cluster_colors = ["#63a9ff", "#ffc45e"]
                render_horizontal_bars(
                    "Movement patterns in this window",
                    "Each bar counts matched 12-hour episodes; Cluster 1 is saved source cluster 2.",
                    [DISPLAY_CLUSTER_LABELS[int(value)] for value in cluster_counts["cluster"].tolist()],
                    cluster_counts["episodes"].tolist(),
                    colors=[cluster_colors[int(value) % len(cluster_colors)] for value in cluster_counts["cluster"].tolist()],
                )
                cluster_table = cluster_counts.rename(columns={"cluster": "Display cluster", "episodes": "Saved episodes"})
                cluster_table["Movement pattern"] = cluster_table["Display cluster"].map(DISPLAY_CLUSTER_NAMES)
                st.dataframe(cluster_table[["Movement pattern", "Saved episodes"]], hide_index=True, width="stretch")
                st.caption("Names describe the typical saved episode; they are not fault labels.")

    with st.expander("Activity by fleet test group"):
        group_summary = (
            filtered.groupby("fleet_test_id", dropna=False)
            .agg(
                vehicles=("vehicle_id", "nunique"),
                tracks=("track_id", "nunique"),
                recorded_km=("distance_km", "sum"),
            )
            .reset_index()
            .sort_values("tracks", ascending=False)
        )
        group_summary["recorded_km"] = group_summary["recorded_km"].round(1)
        st.dataframe(group_summary, hide_index=True, width="stretch")

    st.subheader("Continue your review")
    with st.container(key="quick-actions"):
        actions = [
            ("Anomaly Monitoring", "Review unusual records", ":material/warning:"),
            ("Data Quality", "Check telemetry quality", ":material/fact_check:"),
            ("Cluster Analysis", "Compare movement groups", ":material/scatter_plot:"),
        ]
        for title, label, icon in actions:
            page_link = get_page_link(title)
            if page_link is not None:
                st.page_link(page_link, label=label, icon=icon)
