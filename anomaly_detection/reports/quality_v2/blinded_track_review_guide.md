# Track review guide

Share `blinded_track_review_sheet.csv` with reviewers. Keep `blinded_track_review_key.csv` private until labels are recorded.

For each row, inspect the raw speed trace and available track context. Fill both review fields:

- `telemetry_quality_review`: `adequate`, `problematic`, or `uncertain`.
- `movement_interpretation`: `typical`, `unusual_but_legitimate`, `suspected_movement_anomaly`, or `insufficient_evidence`.

Keep data-quality problems separate from movement findings. If telemetry is problematic, do not treat the track as a confirmed movement anomaly; use the notes to describe the data issue.

The sheet mixes model-alert candidates with a reproducible random sample of tracks not flagged by any of the three rules. Reviewers are blinded to that group and to model scores. The unflagged sample helps find possible missed cases, but 200 cases are only a pilot and will not give a precise recall estimate.

No reviewer outcome is prefilled or inferred by the model.
