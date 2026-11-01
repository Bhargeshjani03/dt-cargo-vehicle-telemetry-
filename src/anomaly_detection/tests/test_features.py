
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1])
)

from src.anomaly_detection.src.features import (
    FEATURE_COLUMNS,
    extract_track_features,
)


class FeatureExtractionTests(unittest.TestCase):

    def test_speed_statistics_and_low_speed_percentage(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 1.0, 2.0],
            "speed": [0.1, 0.2, 1.0],
        })

        features = extract_track_features(speed)

        self.assertAlmostEqual(
            features["raw_speed_mean_kmh"], 1.56
        )
        self.assertAlmostEqual(
            features["raw_speed_std"],
            np.std([0.1, 0.2, 1.0], ddof=1) * 3.6
        )
        self.assertAlmostEqual(
            features["low_speed_time_pct_03"], 50.0
        )
        self.assertEqual(
            features["stop_episode_count_03"], 0
        )

    def test_exactly_thirty_seconds_counts_as_a_stop_episode(self):
        speed = pd.DataFrame({
            "epoch": np.arange(31, dtype=float),
            "speed": np.full(31, 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(
            features["stop_episode_count_03"], 1
        )
        self.assertAlmostEqual(
            features["low_speed_time_pct_03"], 100.0
        )
        self.assertAlmostEqual(
            features["stop_time_pct_03"], 100.0
        )
        self.assertAlmostEqual(
            features["longest_stop_seconds_03"], 30.0
        )

    def test_negative_speeds_are_excluded_and_counted(self):
        telemetry = pd.DataFrame({
            "epoch": [1000, 1001, 1002, 1003],
            "speed": [5.0, 6.0, -2.0, 7.0],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["negative_speed_count"], 1
        )
        self.assertEqual(
            result["invalid_observation_count"], 1
        )
        self.assertEqual(
            result["observation_count"], 4
        )
        self.assertAlmostEqual(
            result["raw_speed_mean_kmh"], 6.0 * 3.6
        )

    def test_shorter_than_thirty_seconds_does_not_count_as_stop(self):
        speed = pd.DataFrame({
            "epoch": np.arange(30, dtype=float),
            "speed": np.full(30, 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(
            features["stop_episode_count_03"], 0
        )
        self.assertAlmostEqual(
            features["longest_stop_seconds_03"], 0.0
        )

    def test_intervals_over_two_seconds_are_excluded(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 2.0, 4.1, 6.1],
            "speed": [0.1, 0.1, 0.5, 0.5],
        })

        features = extract_track_features(speed)

        self.assertEqual(
            features["valid_interval_count"], 2
        )
        self.assertEqual(
            features["excluded_interval_count"], 1
        )
        self.assertAlmostEqual(
            features["valid_telemetry_time_seconds"], 4.0
        )
        self.assertAlmostEqual(
            features["low_speed_time_pct_03"], 50.0
        )

    def test_gap_splits_stop_episodes(self):
        epochs = list(range(15)) + list(range(20, 35))

        speed = pd.DataFrame({
            "epoch": epochs,
            "speed": np.full(len(epochs), 0.1),
        })

        features = extract_track_features(speed)

        self.assertEqual(
            features["stop_episode_count_03"], 0
        )
        self.assertAlmostEqual(
            features["low_speed_time_pct_03"], 100.0
        )

    def test_invalid_rows_are_counted_and_excluded(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 1.0, None, 2.0],
            "speed": [0.1, 0.5, 1.0, "invalid"],
        })

        features = extract_track_features(speed)

        self.assertEqual(
            features["observation_count"], 4
        )
        self.assertEqual(
            features["invalid_observation_count"], 2
        )
        self.assertAlmostEqual(
            features["raw_speed_mean_kmh"], 1.92
        )

    def test_negative_speed_breaks_interval_continuity(self):
        telemetry = pd.DataFrame({
            "epoch": [1000, 1001, 1002, 1003],
            "speed": [5.0, -2.0, 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["negative_speed_count"], 1
        )
        self.assertEqual(
            result["valid_interval_count"], 1
        )
        self.assertEqual(
            result["valid_telemetry_time_seconds"], 1.0
        )
        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_input_dataframe_is_not_modified(self):
        speed = pd.DataFrame({
            "epoch": [2.0, 0.0, 1.0],
            "speed": [2.0, 0.0, 1.0],
        })

        original = speed.copy(deep=True)

        extract_track_features(speed)

        pd.testing.assert_frame_equal(speed, original)

    def test_missing_columns_raise_clear_error(self):
        speed = pd.DataFrame({
            "time": [0.0, 1.0],
            "speed": [1.0, 2.0],
        })

        with self.assertRaisesRegex(ValueError, "epoch"):
            extract_track_features(speed)

    def test_negative_speed_splits_stop_episode(self):
        telemetry = pd.DataFrame({
            "epoch": [1000, 1010, 1020, 1030, 1040, 1050],
            "speed": [0.1, 0.1, -2.0, 0.1, 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["negative_speed_count"], 1
        )

        # All intervals exceed the 2-second limit.
        self.assertEqual(
            result["valid_interval_count"], 0
        )

        # No valid telemetry time means stop metrics are unknown.
        self.assertTrue(
            np.isnan(result["stop_episode_count_03"])
        )
        self.assertTrue(
            np.isnan(result["stop_time_pct_03"])
        )
        self.assertTrue(
            np.isnan(result["longest_stop_seconds_03"])
        )

    def test_duplicate_timestamps_break_interval_continuity(self):
        telemetry = pd.DataFrame({
            "epoch": [0, 1, 1, 2, 3],
            "speed": [0.1, 0.1, 0.1, 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["duplicate_timestamp_count"], 2
        )
        self.assertEqual(
            result["valid_interval_count"], 1
        )
        self.assertAlmostEqual(
            result["valid_telemetry_time_seconds"], 1.0
        )
        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_invalid_timestamp_splits_sequence(self):
        telemetry = pd.DataFrame({
            "epoch": [0, 1, None, 2, 3],
            "speed": [0.1, 0.1, 0.1, 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["invalid_timestamp_count"], 1
        )
        self.assertEqual(
            result["valid_interval_count"], 2
        )
        self.assertAlmostEqual(
            result["valid_telemetry_time_seconds"], 2.0
        )
        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_invalid_speed_breaks_interval_continuity(self):
        telemetry = pd.DataFrame({
            "epoch": [0, 1, 2, 3, 4],
            "speed": [0.1, 0.1, "invalid", 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["invalid_speed_count"], 1
        )
        self.assertEqual(
            result["valid_interval_count"], 2
        )
        self.assertAlmostEqual(
            result["valid_telemetry_time_seconds"], 2.0
        )
        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

    def test_both_endpoint_speeds_must_be_below_threshold(self):
        telemetry = pd.DataFrame({
            "epoch": [0, 1, 2],
            "speed": [0.1, 0.5, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["valid_interval_count"], 2
        )
        self.assertAlmostEqual(
            result["low_speed_time_pct_03"], 0.0
        )
        self.assertEqual(
            result["stop_episode_count_03"], 0
        )

        low_speed_telemetry = pd.DataFrame({
            "epoch": [0, 1],
            "speed": [0.1, 0.2],
        })

        low_result = extract_track_features(
            low_speed_telemetry
        )

        self.assertAlmostEqual(
            low_result["low_speed_time_pct_03"], 100.0
        )

    def test_multiple_qualifying_stop_episodes(self):
        epochs = list(range(31)) + list(range(40, 76))

        telemetry = pd.DataFrame({
            "epoch": epochs,
            "speed": np.full(len(epochs), 0.1),
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["stop_episode_count_03"], 2
        )
        self.assertAlmostEqual(
            result["valid_telemetry_time_seconds"], 65.0
        )
        self.assertAlmostEqual(
            result["stop_time_pct_03"], 100.0
        )
        self.assertAlmostEqual(
            result["longest_stop_seconds_03"], 35.0
        )
        self.assertEqual(
            result["stop_episode_durations_seconds_03"],
            [30.0, 35.0]
        )

    def test_stop_time_percentage_uses_all_valid_telemetry_time(self):
        telemetry = pd.DataFrame({
            "epoch": list(range(42)),
            "speed": [0.1] * 31 + [0.5] * 11,
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["stop_episode_count_03"], 1
        )
        self.assertAlmostEqual(
            result["valid_telemetry_time_seconds"], 41.0
        )
        self.assertAlmostEqual(
            result["longest_stop_seconds_03"], 30.0
        )
        self.assertAlmostEqual(
            result["stop_time_pct_03"],
            (30.0 / 41.0) * 100
        )

    def test_invalid_timestamp_and_speed_count_one_invalid_observation(self):
        telemetry = pd.DataFrame({
            "epoch": [0, None, 2],
            "speed": [0.1, -1.0, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["invalid_timestamp_count"], 1
        )
        self.assertEqual(
            result["invalid_speed_count"], 1
        )
        self.assertEqual(
            result["invalid_observation_count"], 1
        )
        self.assertEqual(
            result["observation_count"], 3
        )

    def test_no_valid_intervals_returns_nan_for_stop_metrics(self):
        telemetry = pd.DataFrame({
            "epoch": [0, 5, 10],
            "speed": [0.1, 0.1, 0.1],
        })

        result = extract_track_features(telemetry)

        self.assertEqual(
            result["valid_interval_count"], 0
        )
        self.assertTrue(
            np.isnan(result["stop_episode_count_03"])
        )
        self.assertTrue(
            np.isnan(result["longest_stop_seconds_03"])
        )
        self.assertTrue(
            np.isnan(result["stop_time_pct_03"])
        )
        self.assertEqual(
            result["stop_episode_durations_seconds_03"], []
        )

    def test_feature_columns_interface_remains_stable(self):
        self.assertEqual(
            FEATURE_COLUMNS,
            (
                "raw_speed_mean_kmh",
                "raw_speed_std",
                "low_speed_time_pct_03",
                "stop_episode_count_03",
            )
        )


if __name__ == "__main__":
    unittest.main()
