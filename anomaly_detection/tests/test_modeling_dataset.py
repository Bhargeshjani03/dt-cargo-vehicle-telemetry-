import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.modeling_dataset import build_modeling_table, save_modeling_outputs


def valid_track(track_id, vehicle_id, distance=1000.0, duration=2.0):
    return {
        "track_id": track_id,
        "vehicle_id": vehicle_id,
        "fleet_test_id": 1,
        "start_time": "2024-01-01T10:00:00+00:00",
        "stop_time": "2024-01-01T10:00:02+00:00",
        "duration_seconds": duration,
        "distance": distance,
        "track_gap": 50.0,
        "avg_speed": 5.0,
        "max_speed": 10.0,
        "avg_hdop": 1.0,
        "n_signal_loss": 0,
        "d_signal_loss": 0.0,
        "r_signal_loss": 0.1,
        "home_base": False,
        "long_haul": False,
        "rest_area": False,
        "service_area_fuel": False,
        "industrial_area": False,
    }


def write_speed_file(speed_root, vehicle_id, track_id):
    folder = Path(speed_root) / str(vehicle_id)
    folder.mkdir(parents=True, exist_ok=True)

    pd.DataFrame({
        "epoch": [0.0, 1.0, 2.0],
        "speed": [1.0, 2.0, 3.0],
        "hdop": [1.0, 1.0, 1.0],
    }).to_csv(folder / f"{track_id}.csv", index=False)


class ModelingDatasetTests(unittest.TestCase):
    def test_builds_core_and_extended_tables_without_dropping_tracks(self):
        tracks = [
            valid_track(1001, 11),
            valid_track(1002, 12, distance=0.0),
            valid_track(1003, 13, distance=None, duration=-1.0),
            valid_track(1004, 14),  # No speed file: must remain in the table.
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            speed_root = Path(temp_dir) / "speed"
            for track in tracks[:3]:
                write_speed_file(
                    speed_root,
                    track["vehicle_id"],
                    track["track_id"],
                )

            table, summary = build_modeling_table(
                pd.DataFrame(tracks),
                speed_root=str(speed_root),
            )

        self.assertEqual(len(table), 4)
        self.assertEqual(summary["input_tracks"], 4)

        by_id = table.set_index("track_id")

        self.assertEqual(by_id.loc[1001, "quality_status_core"], "eligible")
        self.assertEqual(
            by_id.loc[1001, "quality_status_extended"], "eligible"
        )

        self.assertEqual(
            by_id.loc[1002, "quality_status_extended"],
            "eligible_with_warnings",
        )
        self.assertEqual(by_id.loc[1002, "distance_km"], 0.0)
        self.assertTrue(by_id.loc[1002, "flag_zero_distance"])

        self.assertEqual(
            by_id.loc[1003, "quality_status_core"],
            "eligible_with_warnings",
        )
        self.assertEqual(
            by_id.loc[1003, "quality_status_extended"],
            "ineligible",
        )
        self.assertIn(
            "duration_invalid",
            by_id.loc[1003, "ineligible_reasons_extended"],
        )

        self.assertEqual(by_id.loc[1004, "quality_status_core"], "ineligible")
        self.assertEqual(
            by_id.loc[1004, "processing_error"],
            "missing_speed_file",
        )

        self.assertEqual(
            summary["models"]["core_four_feature"]["eligible"], 1
        )
        self.assertEqual(
            summary["models"]["core_four_feature"]["eligible_with_warnings"],
            2,
        )
        self.assertEqual(
            summary["models"]["core_four_feature"]["ineligible"], 1
        )

        self.assertEqual(
            summary["models"]["extended_six_feature"]["eligible"], 1
        )
        self.assertEqual(
            summary["models"]["extended_six_feature"]["eligible_with_warnings"],
            1,
        )
        self.assertEqual(
            summary["models"]["extended_six_feature"]["ineligible"], 2
        )

    def test_saves_table_and_summary(self):
        tracks = [valid_track(2001, 21)]

        with tempfile.TemporaryDirectory() as temp_dir:
            speed_root = Path(temp_dir) / "speed"
            output_dir = Path(temp_dir) / "reports"
            write_speed_file(speed_root, 21, 2001)

            table, summary = build_modeling_table(
                pd.DataFrame(tracks),
                speed_root=str(speed_root),
            )
            save_modeling_outputs(table, summary, str(output_dir))

            self.assertTrue((output_dir / "modeling_dataset.csv").is_file())
            self.assertTrue((output_dir / "eligibility_summary.json").is_file())

            with (output_dir / "eligibility_summary.json").open() as file:
                saved_summary = json.load(file)

        self.assertEqual(saved_summary["input_tracks"], 1)


if __name__ == "__main__":
    unittest.main()