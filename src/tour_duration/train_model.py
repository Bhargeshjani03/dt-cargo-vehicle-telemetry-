from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/processed/tour_level/telemetry_flagged_episodes_12h.csv'
ARTIFACTS = ROOT / 'src/tour_duration/artifacts'
FEATURES = [
    'total_distance_km', 'gross_vehicle_weight', 'total_mass_with_trailer',
    'axle_class', 'start_year', 'start_month', 'start_weekday', 'start_hour', 'vehicle_id',
]
TARGET = 'elapsed_span_hours'


def make_model():
    return TransformedTargetRegressor(
        regressor=HistGradientBoostingRegressor(
            max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
            min_samples_leaf=20, l2_regularization=1.0,
            early_stopping=False, random_state=42,
        ),
        func=np.log1p,
        inverse_func=np.expm1,
    )


def main():
    if not DATA.is_file():
        raise FileNotFoundError(f'Missing training data: {DATA}')
    frame = pd.read_csv(DATA, low_memory=False)
    required = set(FEATURES + [TARGET, 'start_time', 'telemetry_flagged'])
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f'Training data is missing fields: {sorted(missing)}')
    frame['start_time'] = pd.to_datetime(frame['start_time'], utc=True, errors='coerce')
    for column in FEATURES + [TARGET]:
        frame[column] = pd.to_numeric(frame[column], errors='coerce')
    frame = frame.dropna(subset=['start_time', TARGET]).loc[lambda d: d[TARGET] > 0]
    frame = frame.sort_values('start_time').reset_index(drop=True)
    if len(frame) < 1000:
        raise ValueError('Not enough valid episodes to train the duration model.')
    train_cut = frame['start_time'].iloc[int(0.70 * (len(frame) - 1))]
    holdout_cut = frame['start_time'].iloc[int(0.85 * (len(frame) - 1))]
    train = frame.loc[(frame['start_time'] < holdout_cut) & (~frame['telemetry_flagged'].astype(str).str.lower().isin(['true', '1']))].copy()
    holdout = frame.loc[frame['start_time'] >= holdout_cut].copy()
    if train.empty or holdout.empty:
        raise ValueError('Chronological training or holdout split is empty.')
    model = make_model()
    model.fit(train[FEATURES], train[TARGET])
    predicted = np.maximum(model.predict(holdout[FEATURES]), 0)
    actual = holdout[TARGET].to_numpy(dtype=float)
    metrics = {
        'holdoutEpisodes': int(len(holdout)),
        'r2': float(r2_score(actual, predicted)),
        'maeHours': float(mean_absolute_error(actual, predicted)),
        'rmseHours': float(np.sqrt(mean_squared_error(actual, predicted))),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, ARTIFACTS / 'tour_duration_v1.joblib')
    bounds = {}
    for column in FEATURES:
        values = pd.to_numeric(train[column], errors='coerce').dropna()
        bounds[column] = {'min': float(values.min()), 'max': float(values.max())} if len(values) else None
    metadata = {
        'available': True,
        'modelName': 'HistGradientBoostingRegressor with log-transformed target',
        'version': 'tour-duration-v1',
        'target': 'elapsed_span_hours',
        'features': ['planned_distance_km', 'gross_vehicle_weight', 'total_mass_with_trailer', 'axle_class', 'departure year/month/weekday/hour', 'vehicle_id'],
        'trainingExamples': int(len(train)),
        'trainingStart': train['start_time'].min().isoformat(),
        'trainingEnd': train['start_time'].max().isoformat(),
        'holdoutStart': holdout['start_time'].min().isoformat(),
        'holdoutEnd': holdout['start_time'].max().isoformat(),
        'holdoutMetrics': metrics,
        'inputBounds': bounds,
        'distanceFeatureNote': 'Training data contain completed-tour total_distance_km; the form substitutes user-entered planned distance. This is an explicit proxy assumption, not planned-distance training data.',
        'limitations': [
            'Elapsed span includes gaps and pauses, not only moving time.',
            'The historical distance is recorded after a tour; planned distance is substituted at inference as a proxy.',
            'Holdout scores do not establish accuracy for new routes or operating regimes.',
        ],
    }
    (ARTIFACTS / 'tour_duration_v1.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata, indent=2))


if __name__ == '__main__':
    main()
