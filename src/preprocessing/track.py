
"""
Track-level preprocessing for clustering.

Responsibilities:
1. Combine extracted track features with existing quality assessments.
2. Exclude only tracks marked as ineligible.
3. Preserve quality flags and warning information.
4. Return clustering-ready features without performing scaling or imputation.

Quality assessment is handled by:
    src/anomaly_detection/quality.py
"""

import pandas as pd


TRACK_CLUSTERING_FEATURES = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]


def prepare_track_clustering_data(
    track_features: pd.DataFrame,
    quality_results: pd.DataFrame,
    feature_columns: list = None,
):
    """
    Prepare track-level data for clustering.

    Parameters
    ----------
    track_features : pd.DataFrame
        One row per track, containing track_id and extracted
        movement features from anomaly_detection/features.py.

    quality_results : pd.DataFrame
        Quality assessment results from anomaly_detection/quality.py.
        Must contain track_id and quality_status.

    feature_columns : list, optional
        Features to use for clustering. Defaults to TRACK_CLUSTERING_FEATURES.

    Returns
    -------
    eligible_tracks : pd.DataFrame
        Tracks eligible for clustering, including tracks with warnings.

    excluded_tracks : pd.DataFrame
        Tracks marked as ineligible, with their quality information.
    """

    if feature_columns is None:
        feature_columns = TRACK_CLUSTERING_FEATURES

    # --------------------------------------------------
    # 1. Validate input columns
    # --------------------------------------------------

    required_feature_columns = ["track_id"] + feature_columns
    required_quality_columns = ["track_id", "quality_status"]

    missing_features = [
        col for col in required_feature_columns
        if col not in track_features.columns
    ]

    missing_quality = [
        col for col in required_quality_columns
        if col not in quality_results.columns
    ]

    if missing_features:
        raise ValueError(
            f"Missing columns in track_features: {missing_features}"
        )

    if missing_quality:
        raise ValueError(
            f"Missing columns in quality_results: {missing_quality}"
        )

    # --------------------------------------------------
    # 2. Validate track identifiers
    # --------------------------------------------------

    if track_features["track_id"].duplicated().any():
        raise ValueError(
            "Duplicate track_id found in track_features."
        )

    if quality_results["track_id"].duplicated().any():
        raise ValueError(
            "Duplicate track_id found in quality_results."
        )

    if quality_results["quality_status"].isna().any():
        raise ValueError(
            "Missing quality_status values found. "
            "Resolve quality assessments before clustering."
        )

    valid_statuses = {
        "eligible",
        "eligible_with_warnings",
        "ineligible",
    }

    unknown_statuses = (
        set(quality_results["quality_status"].unique())
        - valid_statuses
    )

    if unknown_statuses:
        raise ValueError(
            f"Unknown quality statuses: {unknown_statuses}"
        )

    # --------------------------------------------------
    # 3. Merge features with quality assessments
    # --------------------------------------------------

    combined = track_features.merge(
        quality_results,
        on="track_id",
        how="inner",
        validate="one_to_one",
    )

    # --------------------------------------------------
    # 4. Identify eligible and ineligible tracks
    # --------------------------------------------------

    eligible_mask = combined["quality_status"].isin(
        ["eligible", "eligible_with_warnings"]
    )

    eligible_tracks = combined.loc[eligible_mask].copy()

    excluded_tracks = combined.loc[~eligible_mask].copy()

    # --------------------------------------------------
    # 5. Select clustering features
    # --------------------------------------------------

    # Keep track_id, selected features, and quality information.
    quality_columns = [
        col for col in quality_results.columns
        if col != "track_id"
    ]

    output_columns = (
        ["track_id"]
        + feature_columns
        + quality_columns
    )

    eligible_tracks = eligible_tracks[output_columns].reset_index(
        drop=True
    )

    excluded_tracks = excluded_tracks.reset_index(drop=True)

    # --------------------------------------------------
    # 6. Print preprocessing summary
    # --------------------------------------------------

    print("TRACK-LEVEL PREPROCESSING SUMMARY")
    print("-" * 40)

    print(f"Feature records: {len(track_features)}")
    print(f"Quality records: {len(quality_results)}")
    print(f"Matched records: {len(combined)}")

    print(
        f"Eligible tracks: "
        f"{(combined['quality_status'] == 'eligible').sum()}"
    )

    print(
        f"Eligible with warnings: "
        f"{(combined['quality_status'] == 'eligible_with_warnings').sum()}"
    )

    print(f"Ineligible tracks: {len(excluded_tracks)}")

    print(f"Clustering features: {feature_columns}")

    print(
        "Missing feature values:",
        int(eligible_tracks[feature_columns].isna().sum().sum()),
    )

    return eligible_tracks, excluded_tracks
