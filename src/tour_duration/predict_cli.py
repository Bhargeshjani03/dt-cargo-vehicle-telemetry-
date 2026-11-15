from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / 'src/tour_duration/artifacts/tour_duration_v1.joblib'
METADATA = ROOT / 'src/tour_duration/artifacts/tour_duration_v1.json'
FEATURES = [
    'total_distance_km', 'gross_vehicle_weight', 'total_mass_with_trailer',
    'axle_class', 'start_year', 'start_month', 'start_weekday', 'start_hour', 'vehicle_id',
]


def main():
    payload = json.load(sys.stdin)
    if not ARTIFACT.is_file() or not METADATA.is_file():
        raise FileNotFoundError('Duration model artifact is missing. Run npm run model:train.')
    metadata = json.loads(METADATA.read_text())
    departure = pd.to_datetime(payload['departureAt'], utc=True, errors='raise')
    row = {
        'total_distance_km': float(payload['plannedDistanceKm']),
        'gross_vehicle_weight': float(payload['grossVehicleWeight']),
        'total_mass_with_trailer': float(payload['totalMassWithTrailer']),
        'axle_class': float(payload['axleClass']),
        'start_year': departure.year,
        'start_month': departure.month,
        'start_weekday': departure.weekday(),
        'start_hour': departure.hour,
        'vehicle_id': float(payload['vehicleId']),
    }
    frame = pd.DataFrame([row], columns=FEATURES)
    model = joblib.load(ARTIFACT)
    hours = max(0.0, float(model.predict(frame)[0]))
    warnings = []
    for feature, value in row.items():
        bounds = metadata.get('inputBounds', {}).get(feature)
        if bounds and (value < bounds['min'] or value > bounds['max']):
            warnings.append(f'{feature} is outside the historical training range.')
    result = {
        'predictedDurationHours': round(hours, 2),
        'modelName': metadata['modelName'],
        'version': metadata['version'],
        'holdoutMetrics': metadata['holdoutMetrics'],
        'warnings': warnings,
        'distanceFeatureNote': metadata['distanceFeatureNote'],
        'limitations': metadata['limitations'],
    }
    print(json.dumps(result))


if __name__ == '__main__':
    main()
