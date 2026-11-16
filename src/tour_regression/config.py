
"""Configuration for DT-CARGO pre-trip tour-duration regression."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Corrected: there is no "input" directory in this dataset location.
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

# K-Means uses historical distance and speed to establish the
# operational categories during training.
CLUSTER_FEATURES = [
    "total_distance_km",
    "distance_based_avg_speed_kmh_clean",
]

# The regression model only receives distance and category.
REGRESSION_FEATURES = [
    "total_distance_km",
]

TREE_FEATURES = [
    "total_distance_km",
    "cluster",
]

TARGET_COLUMN = "elapsed_span_hours"
GAP_COLUMN = "unrecorded_gap_hours"

MODEL_VERSION = "dt-cargo-pretrip-regular-v2"
RANDOM_STATE = 42

# Thresholds are compared using training-only 5-fold CV.
GAP_THRESHOLD_CANDIDATES = [1, 2, 3, 4, 5, 6, 8, 12]

KMEANS_PARAMS = {
    "n_clusters": 2,
    "random_state": RANDOM_STATE,
    "n_init": 10,
}

# Retains the original distance + category tree configuration.
DECISION_TREE_PARAMS = {
    "max_depth": 10,
    "min_samples_split": 10,
    "min_samples_leaf": 5,
    "random_state": RANDOM_STATE,
}
