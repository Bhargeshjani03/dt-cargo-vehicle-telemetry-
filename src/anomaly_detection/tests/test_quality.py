import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.quality import CORE_FEATURES, assess_track_quality


def valid_metadata():
    return {
        "track_id": 123,
        "start_time": "2024-01-01T10:00:00+00:00",
        "stop_time": "2024-01-01T10:00:02+00:00",
        "duration_seconds": 2.0,
        "distance": 1000.0,
        "avg_speed": 5.0,
        "max_speed": 10.0,
        "n_signal_loss": 0,
        "d_signal_loss": 0.0,
        "r_signal_loss": 0.1,
        "track_gap": 50.0,
    }


def valid_speed_data():
    return pd.DataFrame({
        "epoch": [0.0, 1.0, 2.0],
        "speed": [1.0, 2.0, 3.0],
        "hdop": [1.0, 1.0, 1.0],
    })


class QualityGateTests(unittest.TestCase):
    def test_valid_track_is_eligible(self):
        result = assess_track_quality(valid_metadata(), valid_speed_data())
        self.assertEqual(result["quality_status"], "eligible")
        self.assertEqual(result["track_id"], 123)

    def test_one_or_two_observations_are_insufficient(self):
        speed = valid_speed_data().iloc[:2]
        result = assess_track_quality(valid_metadata(), speed)
        self.assertEqual(result["quality_status"], "ineligible")
        self.assertIn("insufficient_telemetry", result["ineligible_reasons"])

    def test_no_valid_time_intervals_are_insufficient(self):
        speed = pd.DataFrame({
            "epoch": [0.0, 3.0, 6.0],
            "speed": [1.0, 2.0, 3.0],
        })
        result = assess_track_quality(valid_metadata(), speed)
        self.assertEqual(result["quality_status"], "ineligible")

    def test_optional_valid_time_cutoff_is_applied_when_supplied(self):
        result = assess_track_quality(
            valid_metadata(),
            valid_speed_data(),
            min_valid_telemetry_seconds=3.0,
        )
        self.assertEqual(result["quality_status"], "ineligible")

    def test_invalid_duration_warns_for_core_model(self):
        track = valid_metadata()
        track["duration_seconds"] = -1.0

        result = assess_track_quality(track, valid_speed_data())
        self.assertEqual(result["quality_status"], "eligible_with_warnings")
        self.assertTrue(result["quality_flags"]["duration_invalid"])

    def test_invalid_duration_blocks_model_that_requires_duration(self):
        track = valid_metadata()
        track["duration_seconds"] = -1.0
        features = CORE_FEATURES + ("duration_minutes", "distance_km")

        result = assess_track_quality(
            track, valid_speed_data(), required_features=features
        )
        self.assertEqual(result["quality_status"], "ineligible")
        self.assertIn("duration_invalid", result["ineligible_reasons"])

    def test_missing_distance_blocks_model_that_requires_distance(self):
        track = valid_metadata()
        track["distance"] = None
        features = CORE_FEATURES + ("duration_minutes", "distance_km")

        result = assess_track_quality(
            track, valid_speed_data(), required_features=features
        )
        self.assertEqual(result["quality_status"], "ineligible")
        self.assertIn("distance_missing", result["ineligible_reasons"])

    def test_zero_distance_is_kept_but_flagged(self):
        track = valid_metadata()
        track["distance"] = 0.0
        track["max_speed"] = 2.0


        # Replace the metadata argument with the intended track.
        result = assess_track_quality(track, valid_speed_data())

        self.assertEqual(result["quality_status"], "eligible_with_warnings")
        self.assertTrue(result["quality_flags"]["zero_distance"])
        self.assertTrue(result["quality_flags"]["zero_distance_speed_issue"])

    def test_summary_speed_issue_does_not_override_reliable_raw_telemetry(self):
        track = valid_metadata()
        track["avg_speed"] = -1.0

        result = assess_track_quality(track, valid_speed_data())
        self.assertEqual(result["quality_status"], "eligible_with_warnings")
        self.assertTrue(result["quality_flags"]["avg_speed_negative"])

    def test_signal_loss_issues_are_warnings_for_core_model(self):
        track = valid_metadata()
        track["n_signal_loss"] = -1
        track["d_signal_loss"] = -5.0
        track["r_signal_loss"] = 1.2

        result = assess_track_quality(track, valid_speed_data())
        self.assertEqual(result["quality_status"], "eligible_with_warnings")
        self.assertTrue(result["quality_flags"]["n_signal_loss_negative"])
        self.assertTrue(result["quality_flags"]["d_signal_loss_invalid"])
        self.assertTrue(result["quality_flags"]["r_signal_loss_out_of_range"])


if __name__ == "__main__":
    unittest.main()
