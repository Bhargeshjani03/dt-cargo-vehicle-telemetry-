"""Fleet overview page."""

import pandas as pd
import streamlit as st

from src.webapp.data import load_overview_data


def render_overview() -> None:
    st.caption("FLEET ACTIVITY")
    st.title("Fleet Overview")
    st.write(
        "Review recorded activity, then follow a fleet or time-period signal into a deeper investigation."
    )

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

    filter_col, date_col = st.columns([1, 2])
    with filter_col:
        fleet_group = st.selectbox(
            "Fleet test group",
            options=["All groups", *fleet_groups],
            format_func=lambda value: str(value),
        )
    with date_col:
        date_range = st.date_input(
            "Activity period",
            value=(first_day, last_day),
            min_value=first_day,
            max_value=last_day,
        )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_day, end_day = date_range
    elif isinstance(date_range, tuple) and len(date_range) == 1:
        start_day = end_day = date_range[0]
    else:
        start_day = end_day = date_range

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
    distance_km = float(filtered["distance"].clip(lower=0).sum(skipna=True))

    st.subheader("Activity summary")
    metrics = st.columns(4)
    metrics[0].metric("Fleet test groups", f"{fleet_count:,}")
    metrics[1].metric("Vehicles active", f"{vehicle_count:,}")
    metrics[2].metric("Tracks recorded", f"{track_count:,}")
    metrics[3].metric("Recorded distance", f"{distance_km:,.0f} km")

    left, right = st.columns([1.5, 1])
    with left:
        st.subheader("Fleet activity over time")
        monthly = filtered.assign(month=filtered["start_time"].dt.strftime("%Y-%m"))
        monthly_counts = (
            monthly.groupby("month", as_index=False)
            .agg(tracks=("track_id", "nunique"))
            .sort_values("month")
        )
        st.line_chart(monthly_counts.set_index("month"))
        st.dataframe(monthly_counts, hide_index=True)

    with right:
        st.subheader("Behavioral cluster mix")
        clusters = (
            filtered.dropna(subset=["cid"])
            .groupby("cid", as_index=False)
            .agg(tracks=("track_id", "nunique"))
            .sort_values("cid")
        )
        if clusters.empty:
            st.caption("No cluster labels are available for this selection.")
        else:
            st.bar_chart(clusters.set_index("cid"))
            st.dataframe(clusters, hide_index=True)

    st.subheader("Activity by fleet test group")
    group_summary = (
        filtered.groupby("fleet_test_id", dropna=False)
        .agg(
            vehicles=("vehicle_id", "nunique"),
            tracks=("track_id", "nunique"),
            recorded_km=("distance", "sum"),
        )
        .reset_index()
        .sort_values("tracks", ascending=False)
    )
    group_summary["recorded_km"] = group_summary["recorded_km"].round(1)
    st.dataframe(group_summary, hide_index=True)

    if anomalies.empty:
        st.caption("Anomaly validation results are not available in this checkout.")
    else:
        flagged = anomalies.loc[anomalies["is_anomaly"]]
        st.subheader("Anomaly model validation")
        st.metric("Flagged validation tracks", f"{flagged['track_id'].nunique():,}")
        st.caption(
            "This count covers the scored validation set, not every track in the fleet."
        )
