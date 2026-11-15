# DT-CARGO application pages

For a guided tour of the website, model choices, references, and simulations, open the [Project Walkthrough](PROJECT_WALKTHROUGH.md) or choose **Project Walkthrough** from the app’s **Explore all pages** menu.

## Navigation and primary actions

| Page | Main analyst action |
| --- | --- |
| Home | See the available fleet snapshot and open a main analysis. |
| Fleet Overview | Review recorded activity and saved operational signals. |
| Anomaly Monitoring | Filter unusual tracks and inspect their saved evidence. |
| Vehicle Explorer | Follow one vehicle’s recorded history. |
| Track Explorer | Inspect a track’s summary, speed pattern, stops, and data quality. |
| Tour Duration Prediction | Estimate elapsed duration for a configured hypothetical departure. |
| Cluster Analysis | Compare the two movement groups currently displayed by the app. |
| Data Distribution | Explore how recorded measurements are distributed. |
| Data Quality | Review missing, inconsistent, and model-ineligible records. |
| Model Insights | Read model methods, evaluation details, and limitations. |
| 3D Speed Simulator | Replay measured speed from a selected saved track in a schematic scene. |
| Project & Dataset | Read the dataset scope and project context. |
| Project Walkthrough | Follow the project’s data, model, reference, and simulation story step by step. |

## Data boundaries

- Track, quality, anomaly, and cluster views use the project’s processed files. Cluster assignments map source cluster 0 to display Cluster 0 and source cluster 2 to display Cluster 1; source cluster 1 is omitted from the current display.
- No latitude/longitude coordinates are used by the app’s route scenes. The 3D road and cluster paths are illustrations, not GPS playback.
- Anomaly scores are relative unusualness scores, not probabilities or confirmed incidents. The saved model does not provide per-feature causal attribution.
- The duration form substitutes user-entered planned distance for historical completed-tour distance. This is an explicit proxy assumption, not a model trained on planned routes.
- The recorded speed replay uses the selected raw speed file, converts m/s to km/h, and moves a truck through a schematic scene. It does not simulate traffic or explain why a stop occurred.
- MongoDB is optional. With no `MONGODB_URI`, the API reads the local CSV snapshot. `npm run db:import` performs idempotent upserts and does not delete existing records.

## Responsive and input behavior

The top **Explore all pages** menu keeps destinations reachable without a persistent sidebar. Tables can scroll, charts resize with the page, and 3D models support mouse and touch interaction with labeled on-screen controls. Reduced-motion preferences reduce optional animation.
