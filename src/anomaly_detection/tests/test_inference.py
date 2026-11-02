
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from src.inference import (
    _validate_bundle,
    score_batch,
)


FEATURES = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
]


class FakeModel:
    """Small deterministic model for inference tests."""

    n_features_in_ = 4

    def __init__(self, score):
        self.score = score
        self.last_input = None

    def decision_function(self, X):
        self.last_input = X.copy()
        return np.array([-self.score])


def make_bundle(cluster, score=0.05, threshold=0.10):
    return {
        "cluster": cluster,
        "model": FakeModel(score),
        "feature_names": FEATURES,
        "threshold": threshold,
        "model_version": f"test_cluster_{cluster}_v1",
        "transform": "identity",
        "score_direction": "higher_is_more_anomalous",
    }


def valid_track(track_id, vehicle_id, cluster):
    return {
        "track_id": track_id,
        "vehicle_id": vehicle_id,
        "cluster": cluster,
        "start_time": "2024-01-01T10:00:00+00:00",
        "stop_time": "2024-01-01T10:01:00+00:00",
        "duration_seconds": 60.0,
        "distance": 1000.0,
        "avg_speed": 5.0,
        "max_speed": 10.0,
        "n_signal_loss": 0,
        "d_signal_loss": 0.0,
        "r_signal_loss": 0.0,
        "track_gap": 0.0,
    }


def valid_speed():
    return pd.DataFrame({
        "epoch": [0, 1, 2, 3],
        "speed": [2.0, 2.2, 2.4, 2.1],
    })


class ClusterInferenceTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.speed_root = Path(self.temp_dir.name)

        self.bundles = {
            0: make_bundle(0, score=0.05, threshold=0.10),
            1: make_bundle(1, score=0.20, threshold=0.15),
            2: make_bundle(2, score=0.08, threshold=0.10),
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_speed_file(self, vehicle_id, track_id):
        folder = self.speed_root / str(vehicle_id)
        folder.mkdir(parents=True, exist_ok=True)

        path = folder / f"{track_id}.csv"
        valid_speed().to_csv(path, index=False)

        return path

    def test_cluster_0_uses_cluster_0_model(self):
        track = valid_track(1, 10, 0)
        self.create_speed_file(10, 1)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results.iloc[0]["cluster"], 0)
        self.assertEqual(
            results.iloc[0]["model_version"],
            "test_cluster_0_v1",
        )
        self.assertAlmostEqual(
            results.iloc[0]["threshold"],
            0.10,
        )
        self.assertFalse(results.iloc[0]["is_anomaly"])

        self.assertIsNotNone(
            self.bundles[0]["model"].last_input
        )

        self.assertIsNone(
            self.bundles[1]["model"].last_input
        )

    def test_cluster_1_uses_cluster_1_model(self):
        track = valid_track(2, 10, 1)
        self.create_speed_file(10, 2)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(result["cluster"], 1)
        self.assertEqual(
            result["model_version"],
            "test_cluster_1_v1",
        )
        self.assertAlmostEqual(
            result["threshold"],
            0.15,
        )
        self.assertTrue(result["is_anomaly"])

        self.assertIsNotNone(
            self.bundles[1]["model"].last_input
        )

        self.assertIsNone(
            self.bundles[0]["model"].last_input
        )

    def test_cluster_2_uses_cluster_2_model(self):
        track = valid_track(3, 10, 2)
        self.create_speed_file(10, 3)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(result["cluster"], 2)
        self.assertEqual(
            result["model_version"],
            "test_cluster_2_v1",
        )
        self.assertFalse(result["is_anomaly"])

        self.assertIsNotNone(
            self.bundles[2]["model"].last_input
        )

    def test_missing_cluster_is_unassigned(self):
        track = valid_track(4, 10, np.nan)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(
            result["quality_status"],
            "unassigned_cluster",
        )
        self.assertIsNone(result["anomaly_score"])
        self.assertIsNone(result["is_anomaly"])
        self.assertIsNone(result["model_version"])

    def test_unsupported_cluster_is_not_scored(self):
        track = valid_track(5, 10, 3)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(
            result["quality_status"],
            "unsupported_cluster",
        )
        self.assertIsNone(result["anomaly_score"])
        self.assertIsNone(result["is_anomaly"])

    def test_missing_telemetry_file_is_retained(self):
        track = valid_track(6, 10, 0)

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(
            result["processing_error"],
            "missing_speed_file",
        )
        self.assertEqual(
            result["quality_status"],
            "ineligible",
        )
        self.assertIsNone(result["anomaly_score"])

    def test_invalid_telemetry_is_ineligible(self):
        track = valid_track(7, 10, 0)

        folder = self.speed_root / "10"
        folder.mkdir(parents=True, exist_ok=True)

        invalid_speed = pd.DataFrame({
            "epoch": [0, 0, 0],
            "speed": [np.nan, np.nan, np.nan],
        })

        invalid_speed.to_csv(
            folder / "7.csv",
            index=False,
        )

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
        )

        result = results.iloc[0]

        self.assertEqual(
            result["quality_status"],
            "ineligible",
        )
        self.assertIsNone(result["anomaly_score"])
        self.assertIsNone(result["is_anomaly"])

    def test_existing_prediction_is_skipped(self):
        track = valid_track(8, 10, 0)
        self.create_speed_file(10, 8)

        existing = pd.DataFrame({
            "track_id": [8],
            "model_version": ["test_cluster_0_v1"],
        })

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
            existing_predictions=existing,
        )

        self.assertTrue(results.empty)

    def test_different_model_version_is_not_skipped(self):
        track = valid_track(9, 10, 0)
        self.create_speed_file(10, 9)

        existing = pd.DataFrame({
            "track_id": [9],
            "model_version": ["old_cluster_0_v1"],
        })

        results = score_batch(
            pd.DataFrame([track]),
            self.speed_root,
            self.bundles,
            existing_predictions=existing,
        )

        self.assertEqual(len(results), 1)

    def test_wrong_bundle_cluster_raises_error(self):
        track = valid_track(10, 10, 0)

        wrong_bundles = {
            0: make_bundle(1),
        }

        with self.assertRaises(ValueError):
            score_batch(
                pd.DataFrame([track]),
                self.speed_root,
                wrong_bundles,
            )

    def test_bundle_feature_count_is_validated(self):
        bundle = make_bundle(0)
        bundle["feature_names"] = FEATURES[:3]

        with self.assertRaises(ValueError):
            _validate_bundle(bundle)


if __name__ == "__main__":
    unittest.main()
