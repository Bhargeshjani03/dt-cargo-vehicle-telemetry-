
from math import ceil

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from track_analytics_api import (
    get_data,
    dataframe_records,
    get_cluster_information,
    CLUSTERS,
)

router = APIRouter(
    prefix="/api/vehicles",
    tags=["Vehicle Intelligence"],
)

def to_python(value):
    """Convert Pandas/NumPy scalar values to JSON-safe Python values."""

    if value is None:
        return None

    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        value = value.item()

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    return value
def get_vehicle_data():
    data = get_data()

    required = {
        "vehicle_id",
        "track_id",
        "distance_km",
        "duration_minutes",
        "is_anomaly",
        "anomaly_score",
        "quality_status",
        "cluster",
    }

    missing = required - set(data.columns)

    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Missing vehicle analytics columns: {sorted(missing)}",
        )

    return data


def build_vehicle_summary(frame):
    scored = frame[
        frame["anomaly_score"].notna()
    ]

    flagged = scored[
        scored["is_anomaly"]
    ]

    total_scored = len(scored)
    total_flagged = len(flagged)

    rate = (
        total_flagged / total_scored * 100
        if total_scored
        else None
    )

    return {
        "track_count": int(len(frame)),
        "scored_tracks": int(total_scored),
        "unscored_tracks": int(len(frame) - total_scored),
        "flagged_tracks": int(total_flagged),
        "flag_rate_pct": round(rate, 2) if rate is not None else None,
        "total_distance_km": round(
            frame["distance_km"].sum(), 2
        ),
        "median_track_duration_minutes": safe_median(
            frame["duration_minutes"]
        ),
        "first_observed": safe_timestamp(
            frame["start_time"].min()
        ),
        "last_observed": safe_timestamp(
            frame["start_time"].max()
        ),
    }


def safe_median(series):
    value = series.median()
    return round(float(value), 2) if pd.notna(value) else None


def safe_timestamp(value):
    return value.isoformat() if pd.notna(value) else None


def vehicle_records(data):
    records = []

    for vehicle_id, frame in data.groupby(
        "vehicle_id",
        dropna=True,
    ):
        summary = build_vehicle_summary(frame)

        fleet_columns = [
            "fleet_test_id",
            "gross_vehicle_weight",
            "total_mass_with_trailer",
            "axle_class",
        ]

        specifications = {}

        for column in fleet_columns:
            if column in frame.columns:
                value = frame[column].dropna()
                specifications[column] = (
                to_python(value.iloc[0])
                if not value.empty
                else None
            )

        records.append({
            "vehicle_id": int(vehicle_id),
            **specifications,
            **summary,
        })

    return records


@router.get("/summary")
def vehicle_summary():
    data = get_vehicle_data()

    records = vehicle_records(data)

    scored = data[
        data["anomaly_score"].notna()
    ]

    flagged = scored[
        scored["is_anomaly"]
    ]

    return {
        "total_vehicles": int(data["vehicle_id"].nunique()),
        "vehicles_with_scored_tracks": int(
            scored["vehicle_id"].nunique()
        ),
        "total_tracks": int(len(data)),
        "scored_tracks": int(len(scored)),
        "unscored_tracks": int(len(data) - len(scored)),
        "flagged_tracks": int(len(flagged)),
        "overall_flag_rate_pct": round(
            len(flagged) / len(scored) * 100, 2
        ) if len(scored) else None,
        "total_distance_km": round(
            data["distance_km"].sum(), 2
        ),
        "vehicles_with_missing_specs": int(
            data.loc[
                data["gross_vehicle_weight"].isna(),
                "vehicle_id"
            ].nunique()
        ),
    }


@router.get("")
def list_vehicles(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = None,
    minimum_tracks: int = Query(0, ge=0),
    anomaly_only: bool = False,
):
    data = get_vehicle_data()

    records = vehicle_records(data)

    frame = pd.DataFrame(records)

    if search and search.strip():
        term = search.strip().lower()

        mask = frame.apply(
            lambda row: row.astype(str)
            .str.lower()
            .str.contains(term, regex=False)
            .any(),
            axis=1,
        )

        frame = frame.loc[mask]

    frame = frame[
        frame["track_count"] >= minimum_tracks
    ]

    if anomaly_only:
        frame = frame[
            frame["flagged_tracks"] > 0
        ]

    frame = frame.sort_values(
        ["flagged_tracks", "track_count"],
        ascending=[False, False],
    )

    total = len(frame)

    start = (page - 1) * page_size
    selected = frame.iloc[start:start + page_size]

    return {
        "page": page,
        "page_size": page_size,
        "total_vehicles": int(total),
        "total_pages": ceil(total / page_size),
        "records": dataframe_records(selected),
    }


@router.get("/{vehicle_id}/tracks")
def vehicle_track_history(
    vehicle_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    cluster: Optional[int] = Query(None, ge=0, le=2),
    anomaly_status: str = Query(
        "all",
        pattern="^(all|flagged|normal|unscored)$",
    ),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = Query(
        "newest",
        pattern="^(newest|highest_score)$",
    ),
):
    """
    Return paginated track-level records belonging to one vehicle.

    Anomaly flags and scores are inherited from the existing
    track-level Isolation Forest predictions. No vehicle-level
    anomaly model is created here.
    """

    data = get_data()

    required_columns = {
        "track_id",
        "vehicle_id",
        "start_time",
        "stop_time",
        "cluster",
        "anomaly_score",
        "is_anomaly",
    }

    missing = required_columns - set(data.columns)

    if missing:
        raise HTTPException(
            status_code=500,
            detail=(
                "Track dataset is missing required columns: "
                f"{sorted(missing)}"
            ),
        )

    # Exact vehicle matching, not substring matching.
    vehicle_ids = pd.to_numeric(
        data["vehicle_id"],
        errors="coerce",
    )

    frame = data.loc[
        vehicle_ids == vehicle_id
    ].copy()

    if frame.empty:
        raise HTTPException(
            status_code=404,
            detail=f"No tracks found for vehicle {vehicle_id}.",
        )

    # Movement cluster filter.
    if cluster is not None:
        frame = frame.loc[
            pd.to_numeric(
                frame["cluster"],
                errors="coerce",
            ) == cluster
        ]

    # Track-level anomaly status filter.
    scored = pd.to_numeric(
        frame["anomaly_score"],
        errors="coerce",
    ).notna()

    flags = (
        frame["is_anomaly"]
        .astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes"])
    )

    if anomaly_status == "flagged":
        frame = frame.loc[scored & flags]

    elif anomaly_status == "normal":
        frame = frame.loc[scored & ~flags]

    elif anomaly_status == "unscored":
        frame = frame.loc[~scored]

    # Parse dates consistently as UTC.
    frame["start_time"] = pd.to_datetime(
        frame["start_time"],
        errors="coerce",
        utc=True,
    )

    if date_from:
        start = pd.to_datetime(
            date_from,
            errors="coerce",
            utc=True,
        )

        if pd.isna(start):
            raise HTTPException(
                status_code=400,
                detail="Invalid date_from. Use YYYY-MM-DD.",
            )

        frame = frame.loc[
            frame["start_time"] >= start
        ]

    if date_to:
        end = pd.to_datetime(
            date_to,
            errors="coerce",
            utc=True,
        )

        if pd.isna(end):
            raise HTTPException(
                status_code=400,
                detail="Invalid date_to. Use YYYY-MM-DD.",
            )

        # Include the complete date_to day.
        end = end + pd.Timedelta(days=1)

        frame = frame.loc[
            frame["start_time"] < end
        ]

    total_records = len(frame)

    # Sorting.
    if sort_by == "highest_score":
        frame = frame.sort_values(
            "anomaly_score",
            ascending=False,
            na_position="last",
        )
    else:
        frame = frame.sort_values(
            "start_time",
            ascending=False,
            na_position="last",
        )

    # Pagination.
    start_index = (page - 1) * page_size
    selected = frame.iloc[
        start_index:start_index + page_size
    ].copy()

    output_columns = [
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
        "threshold",
        "is_anomaly",
        "low_speed_time_pct_03",
        "stop_episode_count_03",
    ]

    output_columns = [
        column
        for column in output_columns
        if column in selected.columns
    ]

    records = dataframe_records(
        selected[output_columns]
    )

    # Add descriptive cluster metadata.
    for record in records:
        cluster_value = record.get("cluster")

        if cluster_value is None:
            record["cluster_name"] = "Unassigned"
            record["cluster_description"] = (
                "No supported movement cluster assignment."
            )
        else:
            metadata = CLUSTERS.get(int(cluster_value), {})

            record["cluster_name"] = metadata.get(
                "name",
                "Unsupported Cluster",
            )
            record["cluster_description"] = metadata.get(
                "description",
                "No cluster description available.",
            )

    total_pages = (
        (total_records + page_size - 1) // page_size
    )

    return {
        "vehicle_id": int(vehicle_id),
        "page": int(page),
        "page_size": int(page_size),
        "total_records": int(total_records),
        "total_pages": int(total_pages),
        "filters": {
            "cluster": cluster,
            "anomaly_status": anomaly_status,
            "date_from": date_from,
            "date_to": date_to,
            "sort_by": sort_by,
        },
        "records": records,
    }

@router.get("/{vehicle_id}")
def vehicle_detail(vehicle_id: int):
    data = get_vehicle_data()

    frame = data[
        data["vehicle_id"] == vehicle_id
    ].copy()

    if frame.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Vehicle {vehicle_id} not found.",
        )

    summary = build_vehicle_summary(frame)

    fleet_fields = [
        "fleet_test_id",
        "gross_vehicle_weight",
        "total_mass_with_trailer",
        "axle_class",
    ]

    specifications = {}

    for column in fleet_fields:
        if column in frame.columns:
            values = frame[column].dropna()
            specifications[column] = (
        to_python(values.iloc[0])
        if not values.empty
        else None
)

    cluster_counts = (
        frame["cluster"]
        .dropna()
        .value_counts()
        .sort_index()
    )

    cluster_distribution = []

    for cluster_id, count in cluster_counts.items():
        cluster_info = get_cluster_information(cluster_id)

        cluster_distribution.append({
            "cluster": int(cluster_id),
            "name": cluster_info.get("cluster_name"),
            "track_count": int(count),
            "percentage": float(
                round(float(count) / len(frame) * 100, 2)
            ),
        })

    monthly = frame.copy()

    monthly["month"] = (
        monthly["start_time"]
        .dt.to_period("M")
        .astype(str)
    )

    monthly = (
        monthly.groupby("month")
        .agg(
            track_count=("track_id", "count"),
            scored_tracks=("anomaly_score", "count"),
            flagged_tracks=("is_anomaly", "sum"),
        )
        .reset_index()
    )

    monthly["flag_rate_pct"] = (
        monthly["flagged_tracks"]
        / monthly["scored_tracks"].replace(0, pd.NA)
        * 100
    ).round(2)

    monthly = monthly.fillna({
        "flag_rate_pct": 0
    })
    monthly_records = []

    for row in monthly.to_dict(orient="records"):
        monthly_records.append({
            "month": str(row["month"]),
            "track_count": int(row["track_count"]),
            "scored_tracks": int(row["scored_tracks"]),
            "flagged_tracks": int(row["flagged_tracks"]),
            "flag_rate_pct": float(row["flag_rate_pct"]),
        })
    
    return {
        "vehicle_id": vehicle_id,
        "specifications": specifications,
        "summary": summary,
        "cluster_distribution": cluster_distribution,
        "monthly_history": monthly_records,
        "interpretation": (
            "Anomaly statistics aggregate track-level predictions. "
            "They do not represent a separate vehicle-level anomaly model "
            "or confirmed mechanical faults."
        ),
    }
