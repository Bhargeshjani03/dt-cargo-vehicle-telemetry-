# DT-CARGO application pages

## Navigation and primary actions

| Page | Main analyst action |
| --- | --- |
| Fleet Overview | Review anomaly candidates from the selected fleet window. |
| Anomaly Monitoring | Open the highest-scoring visible validation candidate for track investigation. |
| Vehicle Explorer | Open a recent track from the selected vehicle history. |
| Track Explorer | Load a selected track’s detail and telemetry profile. |
| Tour Duration Prediction | Estimate elapsed tour span for a configured hypothetical departure. |
| Behaviour Clusters | Inspect the selected saved cluster’s episode profile. |
| Data Quality & Insights | Review records excluded from the extended anomaly model. |
| Model Insights & Methodology | Review data eligibility and model limits. |
| Mission Simulator | Run or pause an illustrative local dispatch scenario. |

## Data boundaries

- Track, quality, anomaly, and cluster views use the project’s processed files. Track records use `track_id`; cluster assignments use `(vehicle_id, tour_id, episode_no)` and map to tracks by vehicle/tour and start time inside the saved episode window.
- The current join maps 151,398 tracks uniquely and leaves 200 unassigned. Unassigned tracks remain visible and are not forced into a cluster.
- Anomaly scores come from the saved extended six-feature Isolation Forest validation output. The threshold reflects a validation 98th-percentile review policy. Scores are not probabilities, and there are no verified outcome labels.
- Feature values and quality reasons are displayed as context. The saved model does not provide per-feature attribution.
- The speed chart reads the selected track’s raw speed file and converts its source unit (m/s) to km/h.
- There are no route coordinates in the supplied data. The mission route is an illustration, not GPS playback.
- The duration model trains from saved episode data. Historical realized distance is substituted with planned distance at prediction time as an explicit proxy; validate this against planned-route outcomes before operational use.
- MongoDB is optional. With no `MONGODB_URI`, the API reads the local CSV snapshot. `npm run db:import` performs idempotent upserts and does not delete existing records.

## Responsive and input behavior

The sidebar collapses behind a touch-sized menu on narrow viewports. Tables scroll horizontally, charts resize with their containers, cluster bays use full-width touch targets on phones, and the 3D trucks support mouse drag, touch swipe, and focused arrow-key movement. Reduced-motion preferences disable the optional turntable and reduce interface transitions.
