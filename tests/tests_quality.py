import pandas as pd
from anomaly_detection.src.quality import assess_track_quality, CORE_FEATURES

EXTENDED_FEATURES = CORE_FEATURES + ("duration_minutes", "distance_km")


def test_zero_duration_is_invalid_for_extended_model():
    telemetry = pd.DataFrame({
        "epoch": [1000, 1001, 1002],
        "speed": [5.0, 6.0, 5.5],
    })

    track = {
        "track_id": 1,
        "duration_seconds": 0,
        "distance": 1000,
    }

    result = assess_track_quality(
        track, telemetry, required_features=EXTENDED_FEATURES
    )

    assert result["quality_flags"]["duration_invalid"] is True
    assert result["quality_status"] == "ineligible"
    assert "duration_invalid" in result["ineligible_reasons"]
def test_negative_distance_is_invalid_for_extended_model():
    telemetry = pd.DataFrame({
        "epoch": [1000, 1001, 1002],
        "speed": [5.0, 6.0, 5.5],
    })

    track = {
        "track_id": 2,
        "duration_seconds": 2,
        "distance": -100,
    }

    result = assess_track_quality(
        track, telemetry, required_features=EXTENDED_FEATURES
    )

    assert result["quality_flags"]["distance_negative"] is True
    assert result["quality_status"] == "ineligible"
    assert "distance_negative" in result["ineligible_reasons"]
def test_zero_distance_is_not_negative():
    telemetry = pd.DataFrame({
        "epoch": [1000, 1001, 1002],
        "speed": [5.0, 6.0, 5.5],
    })

    track = {
        "track_id": 3,
        "duration_seconds": 2,
        "distance": 0,
    }

    result = assess_track_quality(
        track, telemetry, required_features=EXTENDED_FEATURES
    )

    assert result["quality_flags"]["distance_negative"] is False
    assert result["quality_flags"]["zero_distance"] is True
    assert "distance_negative" not in result["ineligible_reasons"]