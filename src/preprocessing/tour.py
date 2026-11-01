
"""
Tour-level preprocessing for clustering.

Aggregates track-level records by tour_id.

Important:
- Distance is converted from metres to kilometres.
- max_speed is converted from m/s to km/h.
- Speed statistics use only eligible and eligible_with_warnings tracks.
- Distance is aggregated independently using all valid non-negative
  distance values, regardless of telemetry quality status.
- Duration and duration-derived features are never used.
"""

import numpy as np
import pandas as pd


# Primary tour-level clustering features.
TOUR_CLUSTERING_FEATURES = [
    "total_distance_km",
    "mean_track_speed_kmh",
    "max_track_speed_kmh",
]

# Optional feature: may reflect recording segmentation.
OPTIONAL_TOUR_FEATURES = [
    "track_count",
]

ELIGIBLE_STATUSES = {
    "eligible",
    "eligible_with_warnings",
}


def prepare_tour_clustering_data(
    track_data: pd.DataFrame,
    feature_columns: list = None,
    include_track_count: bool = False,
):
    """
    Aggregate track-level data into tour-level clustering data.

    Parameters
    ----------
    track_data : pd.DataFrame
        One row per track. Required columns:
        - track_id
        - tour_id
        - distance       (metres)
        - raw_speed_mean_kmh
        - max_speed      (m/s)
        - quality_status

        The quality_status must come from the existing quality
        assessment pipeline.

    feature_columns : list, optional
        Explicit tour-level clustering features.
        Only approved tour features are accepted.

    include_track_count : bool, default=False
        Whether to include track_count in the default feature set.

    Returns
    -------
    tour_data : pd.DataFrame
        Aggregated tour-level data, including audit columns.

    excluded_tracks : pd.DataFrame
        Tracks marked ineligible. These do not contribute to
        tour-level speed statistics.
    """

    # --------------------------------------------------
    # 1. Select clustering features
    # --------------------------------------------------

    if feature_columns is None:
        feature_columns = TOUR_CLUSTERING_FEATURES.copy()

        if include_track_count:
            feature_columns += OPTIONAL_TOUR_FEATURES

    allowed_features = set(
        TOUR_CLUSTERING_FEATURES + OPTIONAL_TOUR_FEATURES
    )

    unsupported_features = set(feature_columns) - allowed_features

    if unsupported_features:
        raise ValueError(
            "Unsupported tour clustering features: "
            f"{sorted(unsupported_features)}. "
            "Duration and duration-derived features are not allowed."
        )

    if not feature_columns:
        raise ValueError("At least one clustering feature is required.")

    # --------------------------------------------------
    # 2. Validate input
    # --------------------------------------------------

    required_columns = {
        "track_id",
        "tour_id",
        "distance",
        "raw_speed_mean_kmh",
        "max_speed",
        "quality_status",
    }

    missing_columns = required_columns - set(track_data.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    if track_data["track_id"].isna().any():
        raise ValueError("Missing track_id values found.")

    if track_data["tour_id"].isna().any():
        raise ValueError("Missing tour_id values found.")

    if track_data["track_id"].duplicated().any():
        raise ValueError("Duplicate track_id values found.")

    if track_data["quality_status"].isna().any():
        raise ValueError("Missing quality_status values found.")

    valid_statuses = ELIGIBLE_STATUSES | {"ineligible"}

    unknown_statuses = (
        set(track_data["quality_status"].unique()) - valid_statuses
    )

    if unknown_statuses:
        raise ValueError(
            f"Unknown quality statuses: {sorted(unknown_statuses)}"
        )

    # --------------------------------------------------
    # 3. Create a working copy and validate numeric values
    # --------------------------------------------------

    data = track_data.copy()

    data["_distance_m"] = pd.to_numeric(
        data["distance"], errors="coerce"
    )

    data["_raw_speed_mean_kmh"] = pd.to_numeric(
        data["raw_speed_mean_kmh"], errors="coerce"
    )

    data["_max_speed_mps"] = pd.to_numeric(
        data["max_speed"], errors="coerce"
    )

    numeric_columns = [
        "_distance_m",
        "_raw_speed_mean_kmh",
        "_max_speed_mps",
    ]

    data[numeric_columns] = data[numeric_columns].replace(
        [np.inf, -np.inf], np.nan
    )

    # Negative distance and speed values are not used as measurements.
    # Original input columns remain unchanged.
    data.loc[data["_distance_m"] < 0, "_distance_m"] = np.nan

    data.loc[
        data["_raw_speed_mean_kmh"] < 0,
        "_raw_speed_mean_kmh",
    ] = np.nan

    data.loc[
        data["_max_speed_mps"] < 0,
        "_max_speed_mps",
    ] = np.nan

    # --------------------------------------------------
    # 4. Derive distance and maximum speed in standard units
    # --------------------------------------------------

    data["_distance_km"] = data["_distance_m"] / 1000.0

    data["_max_speed_kmh"] = data["_max_speed_mps"] * 3.6

    # --------------------------------------------------
    # 5. Apply existing track quality assessments
    # --------------------------------------------------

    data["_speed_eligible"] = data["quality_status"].isin(
        ELIGIBLE_STATUSES
    )

    data["_eligible_mean_speed"] = data[
        "_raw_speed_mean_kmh"
    ].where(data["_speed_eligible"])

    data["_eligible_max_speed"] = data[
        "_max_speed_kmh"
    ].where(data["_speed_eligible"])

    # --------------------------------------------------
    # 6. Aggregate tracks by tour
    # --------------------------------------------------

    tour_data = (
        data.groupby("tour_id", sort=False)
        .agg(
            total_distance_km=(
                "_distance_km",
                lambda values: values.sum(min_count=1),
            ),

            mean_track_speed_kmh=(
                "_eligible_mean_speed",
                "mean",
            ),

            max_track_speed_kmh=(
                "_eligible_max_speed",
                "max",
            ),

            track_count=(
                "track_id",
                "count",
            ),

            speed_eligible_track_count=(
                "_speed_eligible",
                "sum",
            ),

            distance_valid_track_count=(
                "_distance_km",
                "count",
            ),

            ineligible_track_count=(
                "quality_status",
                lambda values: (values == "ineligible").sum(),
            ),

            warning_track_count=(
                "quality_status",
                lambda values: (
                    values == "eligible_with_warnings"
                ).sum(),
            ),
        )
        .reset_index()
    )

    # --------------------------------------------------
    # 7. Add audit information
    # --------------------------------------------------

    tour_data["partial_quality_coverage"] = (
        tour_data["ineligible_track_count"] > 0
    )

    tour_data["clustering_ready"] = (
        tour_data[feature_columns].notna().all(axis=1)
    )

    # --------------------------------------------------
    # 8. Prepare excluded track records
    # --------------------------------------------------

    excluded_columns = [
        col for col in track_data.columns
        if col in {
            "track_id",
            "tour_id",
            "quality_status",
            "reason_codes",
            "ineligible_reasons_core",
        }
    ]

    excluded_tracks = data.loc[
        data["quality_status"] == "ineligible",
        excluded_columns,
    ].copy().reset_index(drop=True)

    # --------------------------------------------------
    # 9. Print summary
    # --------------------------------------------------

    print("TOUR-LEVEL PREPROCESSING SUMMARY")
    print("-" * 45)

    print(f"Input tracks: {len(data)}")
    print(f"Unique tours: {len(tour_data)}")
    print(f"Excluded tracks: {len(excluded_tracks)}")

    print(
        "Tours with partial quality coverage:",
        int(tour_data["partial_quality_coverage"].sum()),
    )

    print(
        "Tours ready for clustering:",
        int(tour_data["clustering_ready"].sum()),
    )

    print("Selected clustering features:", feature_columns)

    print(
        "Missing values in selected features:",
        int(tour_data[feature_columns].isna().sum().sum()),
    )

    return tour_data, excluded_tracks
