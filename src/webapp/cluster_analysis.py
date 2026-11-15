"""Behavioral cluster profiles based on the saved 12-hour assignments with 3D Spatial Topology."""

import pandas as pd
import streamlit as st

from src.webapp.charts import render_horizontal_bars, render_line_chart, render_metric_grid
from src.webapp.cluster_3d import render_3d_cluster_topology
from src.webapp.data import DISPLAY_CLUSTER_LABELS, DISPLAY_CLUSTER_NAMES, remap_display_clusters, resolve_runtime_path


CLUSTER_PATH = "data/processed/tour_level_clustering/12h_kernelpca_k3_tour_clusters.csv"


@st.cache_data(show_spinner="Loading movement clusters…")
def _read_clusters(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    return pd.read_csv(path, low_memory=False)


def _load_clusters() -> pd.DataFrame:
    path = resolve_runtime_path(CLUSTER_PATH)
    if not path.is_file():
        return pd.DataFrame()
    return remap_display_clusters(_read_clusters(str(path), path.stat().st_mtime_ns))


def _profiles(data: pd.DataFrame) -> pd.DataFrame:
    value_columns = {
        "total_distance_km": "Median distance (km)",
        "elapsed_span_hours": "Median elapsed span (h)",
        "recorded_track_hours": "Median recorded time (h)",
        "track_count": "Median tracks per episode",
        "distance_based_avg_speed_kmh_clean": "Median distance-based speed (km/h)",
        "max_internal_gap_h": "Median longest gap (h)",
    }
    aggregations = {
        "vehicle_id": "nunique",
        **{column: "median" for column in value_columns if column in data.columns},
    }
    grouped = data.groupby("cluster", dropna=False)
    profile = grouped.agg(aggregations)
    profile.insert(0, "Episodes", grouped.size())
    profile.insert(0, "Cluster", profile.index)
    profile = profile.reset_index(drop=True).rename(columns={"vehicle_id": "Vehicles", **value_columns})
    profile.insert(1, "Movement pattern", profile["Cluster"].map(DISPLAY_CLUSTER_NAMES))
    meanings = {
        0: "More distance covered across a few hours; often a fuller moving tour.",
        1: "Little distance across a long elapsed period, with long gaps between recorded tracks.",
    }
    profile.insert(2, "What this usually means", profile["Cluster"].map(meanings))
    return profile.sort_values("Cluster")


def render_cluster_analysis() -> None:
    st.caption("UNDERSTAND")
    st.title("Cluster Analysis")
    st.write("Compare two common movement patterns from the recorded fleet data, then inspect the grouped trucks in 3D.")
    st.caption("Names describe the middle episode in each saved group. Display Cluster 1 is saved source cluster 2.")

    data = _load_clusters()
    required = {"cluster", "vehicle_id", "start_time"}
    if data.empty or not required.issubset(data.columns):
        st.warning("Cluster assignments are not available yet. Configure the processed data folder or Kuberns Storage bucket.")
        return

    data["cluster"] = pd.to_numeric(data["cluster"], errors="coerce")
    data = data.loc[data["cluster"].notna()].copy()
    profiles = _profiles(data)
    if profiles.empty:
        st.info("No valid cluster assignments were found.")
        return

    cluster_info = [
        {
            "id": int(row["Cluster"]),
            "name": DISPLAY_CLUSTER_NAMES[int(row["Cluster"])],
            "episodes": int(row["Episodes"]),
            "vehicles": int(row["Vehicles"]),
        }
        for _, row in profiles.iterrows()
        if pd.notna(row["Cluster"])
    ]

    st.markdown(
        """
        <div style="margin:.8rem 0 1rem;padding:1.2rem 1.4rem 1.35rem;
                    background:linear-gradient(115deg,#1c1917 0%,#292521 74%,#2e291d 100%);
                    border-left:5px solid #feae0f;border-radius:16px;
                    box-shadow:0 14px 30px rgba(28,25,23,.14);">
          <div style="font-size:.72rem;letter-spacing:.14em;color:#feae0f;font-weight:800;">
            DT-CARGO · SAVED TOUR ASSIGNMENTS
          </div>
          <div style="font-family:'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,sans-serif;
                      font-size:clamp(1.9rem,3.8vw,2.8rem);font-weight:800;
                      line-height:1.02;letter-spacing:-.035em;color:#fff;text-transform:uppercase;margin:.55rem 0;">
            TWO MOVEMENT PATTERNS.<br>TWO TRUCKS.
          </div>
          <div style="font-size:.93rem;color:#d6d3d1;max-width:64ch;line-height:1.55;">
            Blue shows longer-distance travel. Amber shows low movement with long gaps. Counts come from saved episodes.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("3D trucks by assigned cluster")
    render_3d_cluster_topology(
        episodes_count=len(data),
        clusters_info=cluster_info,
        height=450,
    )
    st.caption("Truck positions and route paths are illustrative, not GPS locations. These names describe data patterns; they do not label a driver or fault.")

    st.subheader("What these groups look like")
    st.caption("Distances, times, and counts below are medians from the saved episodes, so one unusual episode does not define a whole group.")
    st.dataframe(profiles, hide_index=True, width="stretch")
    cluster_palette = ["#63a9ff", "#ffc45e"]
    render_horizontal_bars(
        "Episode volume by cluster",
        "Each bar counts saved episodes. These names make the common pattern easier to recognize.",
        [DISPLAY_CLUSTER_LABELS[int(value)] for value in profiles["Cluster"].tolist()],
        profiles["Episodes"].tolist(),
        colors=[cluster_palette[int(value) % len(cluster_palette)] for value in profiles["Cluster"].tolist()],
    )

    clusters = sorted(data["cluster"].dropna().unique().tolist())
    selected = st.selectbox("Explore a movement pattern", clusters, format_func=lambda cluster: DISPLAY_CLUSTER_LABELS[int(cluster)])
    selected_data = data.loc[data["cluster"] == selected].copy()

    metrics = [
        ("Episodes", len(selected_data)),
        ("Vehicles", selected_data["vehicle_id"].nunique()),
        ("Typical distance", selected_data.get("total_distance_km", pd.Series(dtype=float)).median()),
        ("Typical elapsed time", selected_data.get("elapsed_span_hours", pd.Series(dtype=float)).median()),
    ]
    units = ["", "", " km", " h"]
    metric_cards = []
    for (label, value), unit in zip(metrics, units):
        if pd.notna(value):
            display_value = f"{int(value):,}" if label in {"Episodes", "Vehicles"} else f"{float(value):,.1f}{unit}"
        else:
            display_value = "—"
        metric_cards.append((label, display_value))
    render_metric_grid(metric_cards, label="Selected movement pattern")

    dates = pd.to_datetime(data["start_time"], errors="coerce", utc=True)
    dated = data.assign(month=dates.dt.strftime("%Y-%m").astype("string")).dropna(subset=["month"])
    monthly = dated.groupby(["month", "cluster"]).size().unstack("cluster", fill_value=0)
    if not monthly.empty:
        st.subheader("Cluster assignments over time")
        cluster_palette = ["#63a9ff", "#ffc45e"]
        series = [
            {
                "label": f"{DISPLAY_CLUSTER_NAMES[int(cluster)]} \u00b7 Cluster {int(cluster)}",
                "values": monthly[cluster].tolist(),
                "color": cluster_palette[int(cluster) % len(cluster_palette)],
            }
            for cluster in monthly.columns
        ]
        render_line_chart(
            "Saved assignments by month",
            "Monthly episode counts for each saved group. Exact values are available on the plotted points and in the episode table below.",
            monthly.index.astype(str).tolist(),
            series,
        )

    st.subheader(f"Recent episodes · {DISPLAY_CLUSTER_LABELS[int(selected)]}")
    detail_columns = [
        "vehicle_id", "tour_id", "episode_no", "start_time", "total_distance_km",
        "elapsed_span_hours", "recorded_track_hours", "track_count",
        "distance_based_avg_speed_kmh_clean", "telemetry_flagged", "source_cluster_id",
    ]
    visible_columns = [column for column in detail_columns if column in selected_data.columns]
    episode_table = selected_data.sort_values("start_time", ascending=False)[visible_columns].head(300)
    episode_table = episode_table.rename(columns={"source_cluster_id": "Saved cluster ID"})
    st.dataframe(episode_table, hide_index=True, width="stretch")

    with st.expander("What these clusters mean"):
        st.markdown(
            "Longer-distance travel usually covers about 156 km over 6.3 elapsed hours. Low movement with long gaps usually covers about 3.5 km over 16.3 hours, with a longest within-episode gap near 6.2 hours. "
            "Check schedules and telemetry before treating long elapsed time as a delay. These names summarize common patterns; they are not operating categories. "
            "Display Cluster 1 maps to saved source ID 2, and the original data and model IDs are unchanged. This assignment file "
            "includes distance, speed, elapsed time, recorded time, and track count; "
            "it does not include stop episode measures, so stopping behavior is not "
            "compared on this page."
        )
