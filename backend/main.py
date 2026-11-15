
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from validation_api import router as validation_router
from track_analytics_api import router as track_analytics_router
from vehicle_intelligence_api import router as vehicle_router
# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "all_track_predictions.csv"

CLUSTERS = {
    0: {
        "name": "Active Transit",
        "description": "Higher-speed movement with comparatively lower low-speed time.",
    },
    1: {
        "name": "Stop-Dominant Movement",
        "description": "Very low movement speed with a typical stop episode.",
    },
    2: {
        "name": "Brief Near-Stationary Tracks",
        "description": "Very low movement speed, typically with no stop episodes.",
    },
}

FEATURE_COLUMNS = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]

TRACK_COLUMNS = [
    "track_id",
    "vehicle_id",
    "start_time",
    "stop_time",
    "cluster",
    "quality_status",
    "telemetry_coverage_ratio",
    "anomaly_score",
    "threshold",
    "is_anomaly",
    "model_version",
    *FEATURE_COLUMNS,
    "quality_flags",
    "reason_codes",
    "raw_speed_path",
    "processing_error",
]


# =========================================================
# APPLICATION
# =========================================================

app = FastAPI(
    title="DT-CARGO API",
    description="Vehicle Telemetry Intelligence Platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATA
# =========================================================

df = None
scored_df = None


def parse_bool(series):
    """Parse CSV boolean values without treating NaN as True."""
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .map({
            "true": True,
            "false": False,
            "1": True,
            "0": False,
        })
        .fillna(False)
        .astype(bool)
    )


@app.on_event("startup")
def load_dataset():
    global df, scored_df

    if not DATA_PATH.exists():
        raise RuntimeError(
            f"Prediction CSV not found: {DATA_PATH}. "
            "Place all_track_predictions.csv inside backend/data/."
        )

    print(f"Loading predictions from {DATA_PATH}")

    data = pd.read_csv(
        DATA_PATH,
        low_memory=False,
    )

    required = [
        "track_id",
        "vehicle_id",
        "cluster",
        "quality_status",
        "anomaly_score",
        "is_anomaly",
        "start_time",
        "threshold",
        *FEATURE_COLUMNS,
    ]

    missing = [
        column for column in required
        if column not in data.columns
    ]

    if missing:
        raise RuntimeError(
            f"Prediction CSV is missing columns: {missing}"
        )

    data["cluster"] = pd.to_numeric(
        data["cluster"], errors="coerce"
    )

    data["anomaly_score"] = pd.to_numeric(
        data["anomaly_score"], errors="coerce"
    )

    data["threshold"] = pd.to_numeric(
        data["threshold"], errors="coerce"
    )

    data["is_anomaly"] = parse_bool(
        data["is_anomaly"]
    )

    data["start_time"] = pd.to_datetime(
        data["start_time"],
        format="mixed",
        errors="coerce",
        utc=True,
    )

    for column in FEATURE_COLUMNS:
        data[column] = pd.to_numeric(
            data[column], errors="coerce"
        )

    df = data

    # Only tracks with an assigned supported cluster and
    # an actual anomaly score belong to the scoring population.
    scored_df = data.loc[
        data["cluster"].isin(CLUSTERS.keys())
        & data["anomaly_score"].notna()
    ].copy()

    print("DT-CARGO dataset loaded successfully.")
    print(f"Total tracks: {len(df):,}")
    print(f"Scored tracks: {len(scored_df):,}")
    print(
        "Flagged tracks:",
        f"{int(scored_df['is_anomaly'].sum()):,}",
    )


def require_data():
    if df is None or scored_df is None:
        raise HTTPException(
            status_code=503,
            detail="Prediction dataset is not loaded.",
        )


def cluster_metadata(value):
    if pd.isna(value):
        return {
            "cluster_id": None,
            "cluster_name": "Unassigned",
            "cluster_description": "No supported movement cluster assignment.",
        }

    cluster_id = int(value)
    metadata = CLUSTERS.get(cluster_id)

    if metadata is None:
        return {
            "cluster_id": cluster_id,
            "cluster_name": "Unsupported Cluster",
            "cluster_description": "No cluster description available.",
        }

    return {
        "cluster_id": cluster_id,
        "cluster_name": metadata["name"],
        "cluster_description": metadata["description"],
    }


def records_to_json(frame):
    """Convert pandas values to JSON-safe Python values."""
    output = frame.copy()

    for column in output.columns:
        if isinstance(
            output[column].dtype,
            pd.DatetimeTZDtype,
        ):
            output[column] = output[column].map(
                lambda value: (
                    value.isoformat()
                    if pd.notna(value)
                    else None
                )
            )

    output = output.astype(object).where(
        pd.notna(output), None
    )

    return output.to_dict(orient="records")


# =========================================================
# HEALTH
# =========================================================

@app.get("/")
def root():
    return {
        "application": "DT-CARGO",
        "version": "2.0.0",
        "status": "running",
    }


@app.get("/api/health")
def health():
    require_data()

    return {
        "status": "healthy",
        "dataset_loaded": True,
        "total_tracks": len(df),
        "scored_tracks": len(scored_df),
    }


# =========================================================
# OVERALL SUMMARY
# =========================================================

@app.get("/api/anomalies/summary")
def anomaly_summary():
    require_data()

    total_tracks = len(df)
    scored_tracks = len(scored_df)

    flagged = int(
        scored_df["is_anomaly"].sum()
    )

    unassigned = int(
        df["cluster"].isna().sum()
    )

    quality_counts = (
        df["quality_status"]
        .value_counts(dropna=False)
        .to_dict()
    )

    return {
        "total_tracks": total_tracks,
        "scored_tracks": scored_tracks,
        "flagged_tracks": flagged,
        "normal_tracks": scored_tracks - flagged,
        "unassigned_tracks": unassigned,
        "flag_rate_pct": round(
            flagged / scored_tracks * 100, 2
        ) if scored_tracks else 0,
        "processing_errors": int(
            df["processing_error"].notna().sum()
        ) if "processing_error" in df.columns else 0,
        "quality_status_counts": {
            str(key): int(value)
            for key, value in quality_counts.items()
        },
        "model": "Cluster-specific Isolation Forest",
        "score_definition": (
            "Negative Isolation Forest decision_function. "
            "Higher scores indicate more unusual observations; "
            "scores are not probabilities."
        ),
    }


# =========================================================
# QUALITY SUMMARY
# =========================================================

@app.get("/api/anomalies/quality")
def quality_summary():
    require_data()

    result = (
        df["quality_status"]
        .fillna("unknown")
        .value_counts()
        .rename_axis("quality_status")
        .reset_index(name="tracks")
    )

    return records_to_json(result)


# =========================================================
# CLUSTER ANALYSIS
# =========================================================

@app.get("/api/anomalies/clusters")
def cluster_analysis():
    require_data()

    grouped = (
        scored_df
        .groupby("cluster")
        .agg(
            tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
            threshold=("threshold", "first"),
            median_speed=("raw_speed_mean_kmh", "median"),
            median_speed_std=("raw_speed_std", "median"),
            median_low_speed_pct=(
                "low_speed_time_pct_03", "median"
            ),
            median_stop_episodes=(
                "stop_episode_count_03", "median"
            ),
        )
        .reset_index()
    )

    output = []

    for _, row in grouped.iterrows():
        cluster_id = int(row["cluster"])
        tracks = int(row["tracks"])
        flagged = int(row["flagged_tracks"])

        metadata = cluster_metadata(cluster_id)

        output.append({
            **metadata,
            "tracks": tracks,
            "flagged_tracks": flagged,
            "normal_tracks": tracks - flagged,
            "flag_rate_pct": round(
                flagged / tracks * 100, 2
            ) if tracks else 0,
            "threshold": float(row["threshold"]),
            "median_speed_kmh": float(
                row["median_speed"]
            ),
            "median_speed_std": float(
                row["median_speed_std"]
            ),
            "median_low_speed_pct": float(
                row["median_low_speed_pct"]
            ),
            "median_stop_episodes": float(
                row["median_stop_episodes"]
            ),
        })

    return output


# =========================================================
# MONTHLY ANALYSIS
# =========================================================

@app.get("/api/anomalies/monthly")
def monthly_analysis():
    require_data()

    monthly = scored_df.dropna(
        subset=["start_time"]
    ).copy()

    monthly["month"] = (
        monthly["start_time"]
        .dt.strftime("%Y-%m")
    )

    result = (
        monthly
        .groupby("month")
        .agg(
            tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
        )
        .reset_index()
        .sort_values("month")
    )

    result["flag_rate_pct"] = (
        result["flagged_tracks"]
        / result["tracks"] * 100
    ).round(2)

    return records_to_json(result)


# =========================================================
# VEHICLE REVIEW
# =========================================================

@app.get("/api/anomalies/vehicles")
def vehicle_analysis(
    limit: int = Query(20, ge=1, le=200),
    min_tracks: int = Query(30, ge=1),
):
    require_data()

    result = (
        scored_df
        .groupby("vehicle_id")
        .agg(
            tracks=("track_id", "count"),
            flagged_tracks=("is_anomaly", "sum"),
        )
        .reset_index()
    )

    result = result.loc[
        result["tracks"] >= min_tracks
    ].copy()

    result["flag_rate_pct"] = (
        result["flagged_tracks"]
        / result["tracks"] * 100
    ).round(2)

    result = result.sort_values(
        ["flagged_tracks", "flag_rate_pct"],
        ascending=False,
    ).head(limit)

    return records_to_json(result)


# =========================================================
# TRACK EXPLORER
# =========================================================

@app.get("/api/anomalies/tracks")
def track_explorer(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    cluster: Optional[int] = Query(None, ge=0, le=2),
    anomaly_only: bool = False,
    quality_status: Optional[str] = None,
):
    require_data()

    result = scored_df

    if search and search.strip():
        term = search.strip()

        mask = (
            result["track_id"].astype(str).str.contains(
                term, case=False, regex=False
            )
            |
            result["vehicle_id"].astype(str).str.contains(
                term, case=False, regex=False
            )
        )

        result = result.loc[mask]

    if cluster is not None:
        result = result.loc[
            result["cluster"] == cluster
        ]

    if anomaly_only:
        result = result.loc[
            result["is_anomaly"]
        ]

    if quality_status:
        result = result.loc[
            result["quality_status"] == quality_status
        ]

    total = len(result)

    result = result.sort_values(
        "anomaly_score",
        ascending=False,
    )

    start = (page - 1) * page_size
    end = start + page_size

    columns = [
        column for column in TRACK_COLUMNS
        if column in result.columns
    ]

    records = records_to_json(
        result.iloc[start:end][columns]
    )

    for record in records:
        record.update(
            cluster_metadata(record.get("cluster"))
        )

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total,
        "total_pages": (
            (total + page_size - 1) // page_size
        ),
        "records": records,
    }


# =========================================================
# INDIVIDUAL TRACK
# =========================================================

@app.get("/api/anomalies/tracks/{track_id}")
def track_details(track_id: str):
    require_data()

    match = df.loc[
        df["track_id"].astype(str) == track_id
    ]

    if match.empty:
        raise HTTPException(
            status_code=404,
            detail="Track not found.",
        )

    record = records_to_json(match.iloc[[0]])[0]

    record.update(
        cluster_metadata(record.get("cluster"))
    )
    return record
# =========================================================
# TOUR REGRESSION VALIDATION
# =========================================================

app.include_router(validation_router)
app.include_router(track_analytics_router)
app.include_router(vehicle_router)