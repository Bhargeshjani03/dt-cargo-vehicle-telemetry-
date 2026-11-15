
from functools import lru_cache
from pathlib import Path
from typing import Optional
import json
import math

import numpy as np
import pandas as pd

from fastapi import APIRouter, HTTPException, Query


router = APIRouter(
    prefix="/api/tracks",
    tags=["Track Analytics"]
)


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRACKS_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "tracks"
    / "tracks.csv"
)

PREDICTIONS_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "all_track_predictions.csv"
)

SPEED_ROOT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "speed"
)

FLEET_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "fleets"
    / "fleet.csv"
)
# =========================================================
# MOVEMENT CLUSTER INFORMATION
# =========================================================

CLUSTERS = {
    0: {
        "name": "Active Transit",
        "description": (
            "Higher-speed movement with comparatively "
            "lower low-speed time."
        )
    },
    1: {
        "name": "Stop-Dominant Movement",
        "description": (
            "Very low movement speed with a typical "
            "stop episode."
        )
    },
    2: {
        "name": "Brief Near-Stationary Tracks",
        "description": (
            "Very low movement speed, typically "
            "with no stop episodes."
        )
    }
}


PREDICTION_COLUMNS = [
    "track_id",
    "quality_status",
    "telemetry_coverage_ratio",
    "anomaly_score",
    "is_anomaly",
    "threshold",
    "model_version",
    "cluster",
    "raw_speed_path",
    "quality_flags",
    "reason_codes",
    "telemetry_evidence",
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
    "processing_error"
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def parse_boolean(series):

    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False
        })
        .fillna(False)
        .astype(bool)
    )


def safe_number(value):

    if pd.isna(value):
        return None

    value = float(value)

    if not math.isfinite(value):
        return None

    return value


def parse_json_value(value):

    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if pd.isna(value):
        return None

    try:
        return json.loads(value)

    except (TypeError, ValueError, json.JSONDecodeError):
        return value


def dataframe_records(frame):

    output = frame.copy()

    for column in output.columns:

        if pd.api.types.is_datetime64_any_dtype(
            output[column]
        ):
            output[column] = output[column].map(
                lambda value: (
                    value.isoformat()
                    if pd.notna(value)
                    else None
                )
            )

    output = output.replace({
        np.nan: None,
        np.inf: None,
        -np.inf: None
    })

    return output.to_dict(orient="records")


def get_cluster_information(value):

    if pd.isna(value):

        return {
            "cluster_id": None,
            "cluster_name": "Unassigned",
            "cluster_description": (
                "No supported movement cluster assignment."
            )
        }

    cluster_id = int(value)

    cluster = CLUSTERS.get(cluster_id)

    if cluster is None:

        return {
            "cluster_id": cluster_id,
            "cluster_name": "Unsupported Cluster",
            "cluster_description": (
                "No cluster description available."
            )
        }

    return {
        "cluster_id": cluster_id,
        "cluster_name": cluster["name"],
        "cluster_description": cluster["description"]
    }


# =========================================================
# LOAD AND MERGE DATASETS
# =========================================================

@lru_cache(maxsize=1)
def load_track_data():

    if not TRACKS_PATH.exists():

        raise RuntimeError(
            f"Original tracks CSV not found: {TRACKS_PATH}"
        )

    if not PREDICTIONS_PATH.exists():

        raise RuntimeError(
            f"Prediction CSV not found: {PREDICTIONS_PATH}"
        )

    print("Loading original track metadata...")

    tracks = pd.read_csv(
        TRACKS_PATH,
        low_memory=False
    )

    print("Loading track predictions...")

    predictions = pd.read_csv(
        PREDICTIONS_PATH,
        usecols=lambda column: (
            column in PREDICTION_COLUMNS
        ),
        low_memory=False
    )

    required_columns = {
        "track_id",
        "vehicle_id",
        "tour_id",
        "start_time",
        "stop_time",
        "distance",
        "avg_speed",
        "max_speed"
    }

    missing_columns = (
        required_columns - set(tracks.columns)
    )

    if missing_columns:

        raise RuntimeError(
            f"Missing columns in tracks.csv: "
            f"{sorted(missing_columns)}"
        )

    if "track_id" not in predictions.columns:

        raise RuntimeError(
            "Prediction CSV must contain track_id."
        )

    tracks["track_id"] = pd.to_numeric(
        tracks["track_id"],
        errors="coerce"
    )

    predictions["track_id"] = pd.to_numeric(
        predictions["track_id"],
        errors="coerce"
    )

    # Ensure one prediction row per track.
    predictions = predictions.drop_duplicates(
        subset=["track_id"],
        keep="last"
    )

    # LEFT JOIN: preserve every original track.
    data = tracks.merge(
        predictions,
        on="track_id",
        how="left",
        suffixes=("", "_prediction"),
        validate="one_to_one"
    )
        # =====================================================
    # MERGE FLEET SPECIFICATIONS
    # =====================================================

    if not FLEET_PATH.exists():
        raise RuntimeError(
            f"Fleet CSV not found: {FLEET_PATH}"
        )

    print("Loading fleet specifications...")

    fleet = pd.read_csv(
        FLEET_PATH,
        low_memory=False
    )

    required_fleet_columns = {
        "vehicle_id",
        "fleet_test_id",
        "gross_vehicle_weight",
        "total_mass_with_trailer",
        "axle_class"
    }

    missing_fleet_columns = (
        required_fleet_columns - set(fleet.columns)
    )

    if missing_fleet_columns:
        raise RuntimeError(
            "Missing columns in fleet.csv: "
            f"{sorted(missing_fleet_columns)}"
        )

    # Normalize vehicle identifiers.
    data["vehicle_id"] = pd.to_numeric(
        data["vehicle_id"],
        errors="coerce"
    )

    fleet["vehicle_id"] = pd.to_numeric(
        fleet["vehicle_id"],
        errors="coerce"
    )

    # A vehicle must have at most one specification row.
    if fleet["vehicle_id"].duplicated().any():
        raise RuntimeError(
            "Duplicate vehicle_id values found in fleet.csv."
        )

    # Convert fleet specification columns.
    fleet_numeric_columns = [
        "fleet_test_id",
        "gross_vehicle_weight",
        "total_mass_with_trailer",
        "axle_class"
    ]

    for column in fleet_numeric_columns:
        fleet[column] = pd.to_numeric(
            fleet[column],
            errors="coerce"
        )

    # Preserve every track, even if a fleet specification
    # is unavailable for its vehicle.
    data = data.merge(
        fleet[
            [
                "vehicle_id",
                "fleet_test_id",
                "gross_vehicle_weight",
                "total_mass_with_trailer",
                "axle_class"
            ]
        ],
        on="vehicle_id",
        how="left",
        validate="many_to_one"
    )

    print(
        "Vehicles with fleet specifications:",
        data.loc[
            data["gross_vehicle_weight"].notna(),
            "vehicle_id"
        ].nunique()
    )
    # Convert numeric columns.
    numeric_columns = [
        "distance",
        "avg_speed",
        "max_speed",
        "avg_hdop",
        "track_gap",
        "n_signal_loss",
        "d_signal_loss",
        "r_signal_loss",
        "telemetry_coverage_ratio",
        "anomaly_score",
        "threshold",
        "cluster",
        "raw_speed_mean_kmh",
        "raw_speed_std",
        "low_speed_time_pct_03",
        "stop_episode_count_03"
    ]

    for column in numeric_columns:

        if column in data.columns:

            data[column] = pd.to_numeric(
                data[column],
                errors="coerce"
            )

    # Parse timestamps.
    data["start_time"] = pd.to_datetime(
        data["start_time"],
        format="mixed",
        errors="coerce",
        utc=True
    )

    data["stop_time"] = pd.to_datetime(
        data["stop_time"],
        format="mixed",
        errors="coerce",
        utc=True
    )

    # Track duration.
    data["duration_minutes"] = (
        data["stop_time"] - data["start_time"]
    ).dt.total_seconds() / 60

    # Original dataset units:
    # distance = metres
    # avg_speed = metres/second
    # max_speed = metres/second

    data["distance_km"] = (
        data["distance"] / 1000
    )

    data["avg_speed_kmh"] = (
        data["avg_speed"] * 3.6
    )

    data["max_speed_kmh"] = (
        data["max_speed"] * 3.6
    )

    # Parse anomaly flags.
    if "is_anomaly" in data.columns:

        data["is_anomaly"] = parse_boolean(
            data["is_anomaly"]
        )

    else:

        data["is_anomaly"] = False

    # Preserve missing predictions as unscored.
    if "quality_status" not in data.columns:

        data["quality_status"] = "unscored"

    data["quality_status"] = (
        data["quality_status"].fillna("unscored")
    )

    # Only supported movement clusters.
    data["cluster"] = data["cluster"].where(
        data["cluster"].isin(CLUSTERS.keys())
    )

    print("--------------------------------")
    print("TRACK ANALYTICS DATA LOADED")
    print("--------------------------------")

    print("Total tracks:", len(data))

    print(
        "Vehicles:",
        data["vehicle_id"].nunique()
    )

    print(
        "Tours:",
        data["tour_id"].nunique()
    )

    print(
        "Tracks with anomaly scores:",
        data["anomaly_score"].notna().sum()
    )

    print("--------------------------------")

    return data


def get_data():

    try:

        return load_track_data()

    except RuntimeError as error:

        raise HTTPException(
            status_code=503,
            detail=str(error)
        )


# =========================================================
# 1. TRACK SUMMARY
# =========================================================

@router.get("/summary")
def track_summary():

    data = get_data()

    scored = (
        data["cluster"].notna()
        & data["anomaly_score"].notna()
    )

    valid_distance = (
        data["distance_km"].notna()
        & data["distance_km"].ge(0)
    )

    valid_duration = (
        data["duration_minutes"].notna()
        & data["duration_minutes"].ge(0)
    )

    quality_counts = (
        data["quality_status"]
        .value_counts()
        .to_dict()
    )

    return {

        "total_tracks": int(len(data)),

        "vehicles": int(
            data["vehicle_id"].nunique()
        ),

        "tours": int(
            data["tour_id"].nunique()
        ),

        "scored_tracks": int(scored.sum()),

        "unscored_tracks": int(
            (~scored).sum()
        ),

        "total_distance_km": round(
            float(
                data.loc[
                    valid_distance,
                    "distance_km"
                ].sum()
            ),
            2
        ),

        "median_track_distance_km": safe_number(
            data.loc[
                valid_distance,
                "distance_km"
            ].median()
        ),

        "median_duration_minutes": safe_number(
            data.loc[
                valid_duration,
                "duration_minutes"
            ].median()
        ),

        "date_min": (
            data["start_time"].min().isoformat()
            if data["start_time"].notna().any()
            else None
        ),

        "date_max": (
            data["start_time"].max().isoformat()
            if data["start_time"].notna().any()
            else None
        ),

        "quality_status_counts": {
            str(key): int(value)
            for key, value in quality_counts.items()
        }
    }


# =========================================================
# 2. MONTHLY TRACK TIMELINE
# =========================================================

@router.get("/timeline")
def track_timeline():

    data = get_data()

    frame = data.dropna(
        subset=["start_time"]
    ).copy()

    frame["month"] = (
        frame["start_time"].dt.strftime("%Y-%m")
    )

    grouped = (
        frame.groupby("month")
        .agg(
            tracks=("track_id", "count"),
            vehicles=("vehicle_id", "nunique"),
            scored_tracks=("anomaly_score", "count")
        )
        .reset_index()
        .sort_values("month")
    )

    return dataframe_records(grouped)


# =========================================================
# 3. TRACK DISTRIBUTIONS
# =========================================================

@router.get("/distributions")
def track_distributions():

    data = get_data()

    def create_histogram(
        series,
        bins=20,
        nonnegative=False
    ):

        values = pd.to_numeric(
            series,
            errors="coerce"
        ).dropna()

        if nonnegative:

            values = values[values >= 0]

        if values.empty:

            return []

        counts, edges = np.histogram(
            values,
            bins=bins
        )

        return [

            {
                "from": round(float(edges[i]), 3),

                "to": round(float(edges[i + 1]), 3),

                "count": int(counts[i]),

                "label": (
                    f"{edges[i]:.1f}–{edges[i + 1]:.1f}"
                )
            }

            for i in range(len(counts))

        ]

    return {

        "distance_km": create_histogram(
            data["distance_km"],
            nonnegative=True
        ),

        "duration_minutes": create_histogram(
            data["duration_minutes"],
            nonnegative=True
        ),

        "average_speed_kmh": create_histogram(
            data["avg_speed_kmh"],
            nonnegative=True
        ),

        "maximum_speed_kmh": create_histogram(
            data["max_speed_kmh"],
            nonnegative=True
        ),

        "low_speed_time_pct": create_histogram(
            data["low_speed_time_pct_03"],
            nonnegative=True
        ),

        "stop_episode_count": create_histogram(
            data["stop_episode_count_03"],
            nonnegative=True
        ),

        "speed_variability": create_histogram(
            data["raw_speed_std"],
            nonnegative=True
        )
    }


# =========================================================
# 4. MOVEMENT CLUSTER PROFILES
# =========================================================

@router.get("/clusters")
def track_cluster_profiles():

    data = get_data()

    scored = data.loc[
        data["cluster"].notna()
    ].copy()

    if scored.empty:

        return []

    grouped = (
        scored.groupby("cluster")
        .agg(

            tracks=("track_id", "count"),

            median_distance_km=(
                "distance_km",
                "median"
            ),

            median_duration_minutes=(
                "duration_minutes",
                "median"
            ),

            median_avg_speed_kmh=(
                "avg_speed_kmh",
                "median"
            ),

            median_raw_speed_kmh=(
                "raw_speed_mean_kmh",
                "median"
            ),

            median_low_speed_pct=(
                "low_speed_time_pct_03",
                "median"
            ),

            median_stop_episodes=(
                "stop_episode_count_03",
                "median"
            ),

            anomaly_flagged=(
                "is_anomaly",
                "sum"
            )
        )
        .reset_index()
    )

    output = []

    for row in dataframe_records(grouped):

        cluster_id = int(row["cluster"])

        output.append({

            **get_cluster_information(cluster_id),

            **{
                key: value
                for key, value in row.items()
                if key != "cluster"
            }

        })

    return output


# =========================================================
# 5. DISTANCE VS DURATION RELATIONSHIP
# =========================================================

@router.get("/relationships")
def track_relationships(
    sample_size: int = Query(
        1500,
        ge=100,
        le=5000
    )
):

    data = get_data()

    columns = [
        "track_id",
        "distance_km",
        "duration_minutes",
        "avg_speed_kmh",
        "max_speed_kmh",
        "cluster"
    ]

    frame = data[columns].dropna(
        subset=[
            "distance_km",
            "duration_minutes",
            "avg_speed_kmh"
        ]
    )

    frame = frame.loc[
        frame["distance_km"].ge(0)
        & frame["duration_minutes"].ge(0)
        & frame["avg_speed_kmh"].ge(0)
    ]

    if len(frame) > sample_size:

        frame = frame.sample(
            sample_size,
            random_state=42
        )

    return dataframe_records(frame)


# =========================================================
# 6. TRACK EXPLORER
# =========================================================

@router.get("/explorer")
def track_explorer(

    page: int = Query(1, ge=1),

    page_size: int = Query(
        25,
        ge=1,
        le=100
    ),

    search: Optional[str] = None,

    cluster: Optional[int] = Query(
        None,
        ge=0,
        le=2
    ),

    quality_status: Optional[str] = None,

    anomaly_only: bool = False,

    date_from: Optional[str] = None,

    date_to: Optional[str] = None

):

    data = get_data()

    frame = data

    # Search track, vehicle or tour.
    if search and search.strip():

        term = search.strip()

        mask = (

            frame["track_id"].astype(str).str.contains(
                term,
                case=False,
                regex=False
            )

            | frame["vehicle_id"].astype(str).str.contains(
                term,
                case=False,
                regex=False
            )

            | frame["tour_id"].astype(str).str.contains(
                term,
                case=False,
                regex=False
            )

        )

        frame = frame.loc[mask]

    # Cluster filter.
    if cluster is not None:

        frame = frame.loc[
            frame["cluster"] == cluster
        ]

    # Quality filter.
    if quality_status:

        frame = frame.loc[
            frame["quality_status"] == quality_status
        ]

    # Anomaly filter.
    if anomaly_only:

        frame = frame.loc[
            frame["is_anomaly"]
        ]

    # Start date filter.
    if date_from:

        start = pd.to_datetime(
            date_from,
            utc=True,
            errors="coerce"
        )

        if pd.isna(start):

            raise HTTPException(
                status_code=400,
                detail="Invalid date_from. Use YYYY-MM-DD."
            )

        frame = frame.loc[
            frame["start_time"] >= start
        ]

    # End date filter.
    if date_to:

        end = pd.to_datetime(
            date_to,
            utc=True,
            errors="coerce"
        )

        if pd.isna(end):

            raise HTTPException(
                status_code=400,
                detail="Invalid date_to. Use YYYY-MM-DD."
            )

        end = end + pd.Timedelta(days=1)

        frame = frame.loc[
            frame["start_time"] < end
        ]

    total = len(frame)

    frame = frame.sort_values(
        "start_time",
        ascending=False,
        na_position="last"
    )

    start_index = (
        (page - 1) * page_size
    )

    selected = frame.iloc[
        start_index:start_index + page_size
    ]

    columns = [

        "track_id",
        "vehicle_id",
        "tour_id",
        "start_time",
        "stop_time",
        "distance_km",
        "duration_minutes",
        "avg_speed_kmh",
        "max_speed_kmh",
        "quality_status",
        "telemetry_coverage_ratio",
        "cluster",
        "anomaly_score",
        "is_anomaly",
        "low_speed_time_pct_03",
        "stop_episode_count_03"

    ]

    columns = [
        column
        for column in columns
        if column in selected.columns
    ]

    records = dataframe_records(
        selected[columns]
    )

    for record in records:

        record.update(
            get_cluster_information(
                record.get("cluster")
            )
        )

    return {

        "page": page,

        "page_size": page_size,

        "total_records": int(total),

        "total_pages": int(
            math.ceil(total / page_size)
        ),

        "records": records

    }


@router.get("/insights")
def operational_insights(
    min_vehicle_tracks: int = Query(30, ge=1, le=1000),
    top_n: int = Query(10, ge=1, le=50),
):
    """
    Operational insights derived from track-level anomaly predictions.

    A flagged track is a statistical outlier according to its
    cluster-specific Isolation Forest model. It is not proof of
    a mechanical fault or operational incident.
    """
    data = get_data()

    # Only include tracks with an actual model score and cluster.
    scored = data.loc[
        data["anomaly_score"].notna()
        & data["cluster"].notna()
    ].copy()

    if scored.empty:
        return {
            "summary": {
                "scored_tracks": 0,
                "flagged_tracks": 0,
                "overall_flag_rate_pct": 0,
                "vehicles_analyzed": 0,
            },
            "priority_vehicles": [],
            "monthly_trend": [],
            "cluster_contribution": [],
            "recurring_reasons": [],
            "minimum_vehicle_tracks": min_vehicle_tracks,
            "interpretation": (
                "No scored tracks are currently available."
            ),
        }

    scored["is_anomaly"] = (
        scored["is_anomaly"].fillna(False).astype(bool)
    )

    total_scored = len(scored)
    total_flagged = int(scored["is_anomaly"].sum())

    # ---------------------------------------------------------
    # 1. Overall summary
    # ---------------------------------------------------------
    overall_rate = (
        total_flagged / total_scored * 100
        if total_scored else 0
    )

    vehicles_analyzed = int(
        scored["vehicle_id"].nunique()
    )

    summary = {
        "scored_tracks": total_scored,
        "flagged_tracks": total_flagged,
        "overall_flag_rate_pct": round(overall_rate, 2),
        "vehicles_analyzed": vehicles_analyzed,
    }

    # ---------------------------------------------------------
    # 2. Vehicle-level review priorities
    # ---------------------------------------------------------
    vehicle_stats = (
        scored.groupby("vehicle_id")
        .agg(
            scored_tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
            first_observed=("start_time", "min"),
            last_observed=("start_time", "max"),
        )
        .reset_index()
    )

    vehicle_stats["flag_rate_pct"] = (
        vehicle_stats["flagged_tracks"]
        / vehicle_stats["scored_tracks"]
        * 100
    )

    # Avoid ranking vehicles with very little observation data.
    eligible_vehicles = vehicle_stats.loc[
        vehicle_stats["scored_tracks"] >= min_vehicle_tracks
    ].copy()

    eligible_vehicles = eligible_vehicles.sort_values(
        ["flag_rate_pct", "flagged_tracks"],
        ascending=[False, False],
    ).head(top_n)

    priority_vehicles = []

    for row in dataframe_records(eligible_vehicles):
        rate = row["flag_rate_pct"]

        if rate >= 10:
            review_level = "High"
        elif rate >= 5:
            review_level = "Elevated"
        else:
            review_level = "Routine"

        priority_vehicles.append({
            "vehicle_id": int(row["vehicle_id"]),
            "scored_tracks": int(row["scored_tracks"]),
            "flagged_tracks": int(row["flagged_tracks"]),
            "flag_rate_pct": round(float(rate), 2),
            "review_level": review_level,
            "first_observed": row["first_observed"],
            "last_observed": row["last_observed"],
        })

    # ---------------------------------------------------------
    # 3. Monthly anomaly concentration
    # ---------------------------------------------------------
    monthly_data = scored.dropna(
        subset=["start_time"]
    ).copy()

    monthly_data["month"] = (
        monthly_data["start_time"].dt.strftime("%Y-%m")
    )

    monthly = (
        monthly_data.groupby("month")
        .agg(
            scored_tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )

    monthly["flag_rate_pct"] = (
        monthly["flagged_tracks"]
        / monthly["scored_tracks"]
        * 100
    )

    monthly["flag_rate_pct"] = (
        monthly["flag_rate_pct"].round(2)
    )

    # ---------------------------------------------------------
    # 4. Cluster contribution to flagged tracks
    # ---------------------------------------------------------
    cluster_data = (
        scored.groupby("cluster")
        .agg(
            scored_tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
        )
        .reset_index()
    )

    cluster_data["flag_rate_pct"] = (
        cluster_data["flagged_tracks"]
        / cluster_data["scored_tracks"]
        * 100
    )

    cluster_data["share_of_all_flags_pct"] = (
        cluster_data["flagged_tracks"]
        / total_flagged * 100
        if total_flagged else 0
    )

    cluster_contribution = []

    for row in dataframe_records(cluster_data):
        cluster_id = int(row["cluster"])

        cluster_contribution.append({
            **get_cluster_information(cluster_id),
            "scored_tracks": int(row["scored_tracks"]),
            "flagged_tracks": int(row["flagged_tracks"]),
            "flag_rate_pct": round(
                float(row["flag_rate_pct"]), 2
            ),
            "share_of_all_flags_pct": round(
                float(row["share_of_all_flags_pct"]), 2
            ),
        })

    # ---------------------------------------------------------
    # 5. Recurring reason codes among flagged tracks
    # ---------------------------------------------------------
    reason_counts = {}

    flagged_data = scored.loc[
        scored["is_anomaly"]
    ]

    for value in flagged_data["reason_codes"].dropna():
        parsed = parse_json_value(value)

        if isinstance(parsed, list):
            reasons = parsed
        elif isinstance(parsed, str):
            reasons = [parsed]
        else:
            continue

        # Count each reason at most once per flagged track.
        for reason in set(str(item) for item in reasons):
            if reason and reason.lower() != "nan":
                reason_counts[reason] = (
                    reason_counts.get(reason, 0) + 1
                )

    recurring_reasons = [
        {
            "reason_code": reason,
            "flagged_tracks": count,
            "share_of_flagged_tracks_pct": round(
                count / total_flagged * 100, 2
            ) if total_flagged else 0,
        }
        for reason, count in sorted(
            reason_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    ]

    return {
        "summary": summary,
        "priority_vehicles": priority_vehicles,
        "monthly_trend": dataframe_records(monthly),
        "cluster_contribution": cluster_contribution,
        "recurring_reasons": recurring_reasons,
        "minimum_vehicle_tracks": min_vehicle_tracks,
        "interpretation": (
            "Vehicle rankings use only vehicles with at least "
            f"{min_vehicle_tracks} scored tracks. Flag rates represent "
            "the proportion of tracks flagged by the anomaly models; "
            "they are not probabilities of vehicle failure."
        ),
    }

# =========================================================
# 7. INDIVIDUAL TRACK SPEED PROFILE
# =========================================================

@router.get("/{track_id}/speed-profile")
def track_speed_profile(

    track_id: int,

    max_points: int = Query(
        1200,
        ge=100,
        le=5000
    )

):

    data = get_data()

    match = data.loc[
        data["track_id"] == track_id
    ]

    if match.empty:

        raise HTTPException(
            status_code=404,
            detail="Track not found."
        )

    vehicle_id = int(
        match.iloc[0]["vehicle_id"]
    )

    speed_path = (
        SPEED_ROOT
        / str(vehicle_id)
        / f"{track_id}.csv"
    ).resolve()

    # Protect against paths outside the speed directory.
    try:

        speed_path.relative_to(
            SPEED_ROOT.resolve()
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid speed telemetry path."
        )

    if not speed_path.exists():

        raise HTTPException(
            status_code=404,
            detail=(
                f"Raw speed telemetry not found "
                f"for track {track_id}."
            )
        )

    try:

        telemetry = pd.read_csv(
            speed_path,
            usecols=lambda column: (
                column in {"epoch", "speed", "hdop"}
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Unable to read speed telemetry: {error}"
        )

    if not {"epoch", "speed"}.issubset(
        telemetry.columns
    ):

        raise HTTPException(
            status_code=422,
            detail=(
                "Speed telemetry must contain "
                "epoch and speed columns."
            )
        )

    telemetry["epoch"] = pd.to_numeric(
        telemetry["epoch"],
        errors="coerce"
    )

    telemetry["speed"] = pd.to_numeric(
        telemetry["speed"],
        errors="coerce"
    )

    if "hdop" in telemetry.columns:

        telemetry["hdop"] = pd.to_numeric(
            telemetry["hdop"],
            errors="coerce"
        )

    telemetry = telemetry.dropna(
        subset=["epoch", "speed"]
    )

    telemetry = telemetry.sort_values(
        "epoch"
    )

    if telemetry.empty:

        raise HTTPException(
            status_code=404,
            detail="No valid speed observations found."
        )

    first_epoch = float(
        telemetry["epoch"].iloc[0]
    )

    telemetry["elapsed_minutes"] = (
        telemetry["epoch"] - first_epoch
    ) / 60

    # Raw speed is in metres/second.
    telemetry["speed_kmh"] = (
        telemetry["speed"] * 3.6
    )

    original_count = len(telemetry)

    # Downsample large files for chart rendering.
    if original_count > max_points:

        indices = np.linspace(
            0,
            original_count - 1,
            num=max_points,
            dtype=int
        )

        telemetry = telemetry.iloc[indices]

    output_columns = [
        column
        for column in [
            "elapsed_minutes",
            "speed_kmh",
            "hdop"
        ]
        if column in telemetry.columns
    ]

    points = dataframe_records(
        telemetry[output_columns]
    )

    return {

        "track_id": int(track_id),

        "vehicle_id": vehicle_id,

        "observation_count": int(original_count),

        "returned_points": len(points),

        "duration_minutes": round(
            float(
                (
                    telemetry["epoch"].max()
                    - first_epoch
                ) / 60
            ),
            3
        ),

        "speed_unit": "km/h",

        "time_axis": (
            "Elapsed minutes from first observation"
        ),

        "points": points

    }


# =========================================================
# 8. INDIVIDUAL TRACK DETAILS
# =========================================================

@router.get("/{track_id}")
def track_detail(track_id: int):

    data = get_data()

    match = data.loc[
        data["track_id"] == track_id
    ]

    if match.empty:

        raise HTTPException(
            status_code=404,
            detail="Track not found."
        )

    row = match.iloc[0]

    columns = [

        "track_id",
        "vehicle_id",
        "tour_id",
        "start_time",
        "stop_time",

        "distance",
        "distance_km",

        "track_gap",

        "avg_speed",
        "avg_speed_kmh",

        "max_speed",
        "max_speed_kmh",

        "duration_minutes",

        "avg_hdop",

        "n_signal_loss",
        "d_signal_loss",
        "r_signal_loss",

        "home_base",
        "long_haul",
        "rest_area",
        "service_area_fuel",
        "industrial_area",
        "cid",

        "quality_status",
        "telemetry_coverage_ratio",

        "cluster",
        "anomaly_score",
        "threshold",
        "is_anomaly",

        "model_version",

        "raw_speed_mean_kmh",
        "raw_speed_std",
        "low_speed_time_pct_03",
        "stop_episode_count_03",

        "quality_flags",
        "reason_codes",
        "telemetry_evidence",

        "processing_error"

    ]

    columns = [
        column
        for column in columns
        if column in match.columns
    ]

    record = dataframe_records(
        match[columns]
    )[0]

    for key in [
        "quality_flags",
        "reason_codes",
        "telemetry_evidence"
    ]:

        if key in record:

            record[key] = parse_json_value(
                record[key]
            )

    
    record.update(
        get_cluster_information(
            row.get("cluster")
        )
    )

# -----------------------------------------------------
# ANOMALY EVIDENCE
# -----------------------------------------------------

    score = safe_number(record.get("anomaly_score"))
    threshold = safe_number(record.get("threshold"))

    score_margin = None
    score_to_threshold_ratio = None

    if score is not None and threshold is not None:
        score_margin = round(score - threshold, 6)

    if threshold != 0:
        score_to_threshold_ratio = round(
            score / threshold,
            4
        )

    is_flagged = (
    str(record.get("is_anomaly", "")).strip().lower()
    in {"true", "1", "yes"}
    )

    feature_definitions = {
        "raw_speed_mean_kmh": {
            "label": "Mean raw speed",
            "unit": "km/h",
            "description": (
                "Average speed derived from raw speed telemetry."
            ),
        },
        "raw_speed_std": {
            "label": "Speed variability",
            "unit": "km/h",
            "description": (
                "Standard deviation of raw speed observations."
            ),
        },
        "low_speed_time_pct_03": {
            "label": "Low-speed time",
            "unit": "%",
            "description": (
                "Percentage of telemetry time at or below "
                "0.3 m/s."
            ),
        },
        "stop_episode_count_03": {
            "label": "Stop episodes",
            "unit": "episodes",
            "description": (
                "Count of continuous low-speed episodes "
                "meeting the 30-second minimum duration."
            ),
        },
    }

    feature_values = {}

    for feature, metadata in feature_definitions.items():
        value = safe_number(record.get(feature))

        feature_values[feature] = {
            **metadata,
            "value": value,
        }

    if score is None or threshold is None:
        assessment = "unavailable"
        explanation = (
            "A score or cluster-specific threshold is unavailable. "
            "This track cannot be assessed using the threshold comparison."
        )

    elif is_flagged:
        assessment = "flagged"
        explanation = (
            "The Isolation Forest anomaly score exceeds the "
            "threshold for this movement cluster. The track is "
            "statistically unusual relative to the model's learned "
            "reference patterns."
        )

    else:
        assessment = "within_threshold"
        explanation = (
            "The Isolation Forest anomaly score does not exceed "
            "the threshold for this movement cluster."
        )

    record["anomaly_evidence"] = {
        "assessment": assessment,
        "is_flagged": bool(is_flagged),
        "anomaly_score": score,
        "cluster_threshold": threshold,
        "score_margin": score_margin,
        "score_to_threshold_ratio": score_to_threshold_ratio,
        "cluster": record.get("cluster"),
        "model_version": record.get("model_version"),
        "features": feature_values,
        "explanation": explanation,
        "interpretation_note": (
            "Isolation Forest uses the combined feature vector. "
            "It does not provide causal feature attribution. "
            "Individual feature values are descriptive evidence, "
            "not proof that a particular feature caused the flag."
        ),
    }

    return record
