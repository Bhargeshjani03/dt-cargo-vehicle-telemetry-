"""Configuration and paths for DT-CARGO tour regression."""

from pathlib import Path

# This file lives at <project-root>/src/tour_regression/config.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "tour_level"
    / "pca_experiments"
    / "experiment_B_75pct_without_extreme.csv"
)

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
DEFAULT_MODEL_PATH = ARTIFACT_DIR / "hybrid_tour_regression.joblib"

CLUSTER_FEATURES = [
    "total_distance_km",
    "distance_based_avg_speed_kmh_clean",
]

REGRESSION_FEATURES = [
    "total_distance_km",
    "distance_based_avg_speed_kmh_clean",
    "track_count",
]

TARGET_COLUMN = "elapsed_span_hours"
MODEL_VERSION = "dt-cargo-tour-hybrid-v1"
RANDOM_STATE = 42

# These are the exact estimator settings used in the notebook experiment.
KMEANS_PARAMS = {
    "n_clusters": 2,
    "random_state": RANDOM_STATE,
    "n_init": 10,
}

DECISION_TREE_PARAMS = {
    "max_depth": 10,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "random_state": RANDOM_STATE,
}
