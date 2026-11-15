# DT-CARGO — a step-by-step walkthrough for Bhargesh

**Start on Home, then follow this guide inside the app.** It explains what each screen is for, why the project uses each analysis, what the 3D views actually show, and which references influenced the presentation.

## 1. What we are building

DT-CARGO is a vehicle telemetry **machine-learning project**. It helps an analyst or fleet operator understand recorded trips, find tracks that deserve a closer look, compare common movement patterns, and estimate tour duration. The site uses the project files and saved model outputs; it is not a live fleet-control service.

The current processed snapshot read by the app contains **151,598 tracks**, **163 vehicle IDs**, **6 fleet groups**, and about **2,201,457 recorded kilometres**, from **26 August 2021 to 6 February 2024**. The Home page calculates its totals from `data/processed/engineered_tracks.csv`, so the figures follow the data installed with the app. The Git branch does not contain the private processed data or the locally trained duration artifact; a fresh clone needs the project data configured as described in the [README](../README.md) before every data-driven page can populate.

The app has track summaries and raw speed traces. The local files used by the site do not provide GPS coordinates, fuel readings, ignition state, or confirmed incident outcomes. That boundary is why the interface shows historical patterns and review prompts instead of live maps, fuel claims, or confirmed faults.

## 2. A simple walkthrough of the website

| Step | Open this page | Ask this question | What to look at |
| --- | --- | --- | --- |
| 1 | **Home** | What does this project help me understand? | The file-backed fleet totals, the two displayed movement groups, review signals, and shortcuts to each analysis. |
| 2 | **Fleet Overview** | How much recorded activity is in the selected time and fleet group? | Tracks, vehicles, distance, activity over time, movement-group counts, and saved anomaly review candidates. Filters change the view; they do not change the source files. |
| 3 | **Cluster Analysis** | What common trip patterns appear in the saved episodes? | Compare each group’s episode count and typical distance, elapsed time, recorded time, and speed. The profile table uses medians so one unusual episode does not define the group. |
| 4 | **Anomaly Monitoring** | Which saved tracks are most different from the model’s usual pattern? | Sort by unusualness score, filter by vehicle, date, status, and movement group, then open a track and inspect the measured features and data-quality notes. |
| 5 | **Vehicle Explorer / Track Explorer** | What happened in one vehicle or one recorded track? | Review saved history, speed patterns, stops, duration, and data-quality context. A single value is evidence to inspect, not an explanation of cause. |
| 6 | **Tour Duration Prediction** | How long might a configured tour take? | Enter a saved vehicle profile, planned distance, and departure time. Read the estimate as a planning guide, not a promised arrival time. |
| 7 | **Data Distribution / Data Quality / Model Insights** | How are the inputs spread, and what can the models support? | See record distributions, missing or inconsistent telemetry, model eligibility, evaluation details, and known limitations. |
| 8 | **3D Speed Simulator** | How does one real speed trace change during a trip? | Choose one saved track, play or scrub through its speed trace, and compare it with the selected movement group. |

### The model choices in plain language

- **Movement clustering:** the app reads the saved 12-hour episode assignment file. The original file contains source clusters 0, 1, and 2. For this version, we show source **0** as display **Cluster 0** and source **2** as display **Cluster 1**; source cluster 1 is omitted from the displayed comparison. The current saved counts are 8,009 and 2,910 episodes. The names “Longer-distance travel” and “Low movement with long gaps” describe the typical saved episode. They are not driver ratings or fault labels. See [`data.py`](../src/webapp/data.py) and [`cluster_analysis.py`](../src/webapp/cluster_analysis.py).
- **Anomaly review:** the saved Isolation Forest output scores six movement signals: average speed, speed variation, time near zero speed, stop-period count, track duration, and distance. The validation cutoff is set as a review queue policy. A higher score means “more unusual relative to this model,” not “this is a problem” or a probability. The feature values give context; the model does not provide per-feature causal attribution. See [`anomaly.py`](../src/webapp/anomaly.py) and [`features.py`](../src/anomaly_detection/src/features.py).
- **Tour duration:** the current local predictor is a `HistGradientBoostingRegressor` with a log-transformed target. It predicts elapsed tour span, which can include gaps between recorded tracks. Its current saved chronological holdout reports 2,727 episodes, an average miss of about **3.20 hours**, and an RMSE of about **6.63 hours**. These scores summarize a test set; they are not an accuracy guarantee for a new route.
- **Distance caveat:** training records contain completed-tour distance. The form accepts a planned distance and uses it as a proxy for completed distance. This makes a pre-departure estimate possible, but it is an assumption to validate against future planned-versus-actual tours.
- **New notebook study:** [`tour_level_analysis.ipynb`](../notebooks/tour_level_analysis.ipynb) is a separate completed-tour benchmark using 7,563 tours from 97 vehicles and five-fold GroupKFold validation by vehicle. Its reported MAE is 2.01 hours, RMSE is 8.02 hours, and R² is 0.762. It uses after-the-tour signals such as recorded average speed and track count. Those results are **not** the model behind the pre-departure form and are not a ready-to-load prediction artifact. The cluster-specific comparison was mixed: average miss improved slightly while RMSE and R² worsened.

## 3. What the simulations show

| View | What moves or changes | What is real | What is illustrative |
| --- | --- | --- | --- |
| **Cluster Analysis 3D trucks** | Two truck models and colored group markers help compare the selected movement patterns. | Group names, counts, and the profile summaries come from saved cluster assignments. | Truck placement and route paths. They do not represent vehicle coordinates or GPS routes. |
| **Recorded Trip Replay** | A truck advances through a schematic scene as the selected recorded speed trace plays. Play, pause, restart, scrub, speed, zoom, and drag/pinch controls are available. | The selected track ID, vehicle ID, sampled speed, elapsed trace time, and recorded distance when available. Source speed in m/s is displayed as km/h. | The road, direction, scenery, and relative position. No traffic, weather, junctions, navigation, ignition, or cause of a slowdown is simulated. |
| **Tour duration timeline** | The predicted elapsed time is drawn between the chosen departure and an estimated arrival time. | The form inputs and model output. | It is not a route map or live ETA. The estimate can include pauses and long gaps. |
| **Home / overview truck model** | A realistic 3D truck can be rotated with touch or a mouse. | The counts beside it are calculated from the local processed records. | The truck’s position and scene; it is a visual guide, not a live fleet vehicle. |

A useful team exercise on the replay page is: **notice** a near-stop or speed change, **compare** it with the group’s typical track, then **discuss** what extra evidence an operator would need. Near-zero speed alone does not prove idling, a delay, or a fault.

## 4. Which references shaped the project

| Reference | What we took from it | What it does not provide to this project |
| --- | --- | --- |
| [DT-CARGO dataset paper](https://doi.org/10.1016/j.dib.2023.109246) | The research dataset context: anonymized truck track metadata and high-resolution speed traces. The local files and `src/` code determine what the app actually uses. | It does not supply our trained cluster labels, anomaly threshold, or duration-model scores. |
| [Tata Motors Fleet Edge features](https://fleetedge.tatamotors.com/features) and [Fleet Edge app listing](https://apps.apple.com/in/app/tata-motors-fleet-edge/id1556047027) | A clear fleet-operator journey and examples of explaining trip planning, tracking, and analysis in a product. | Fleet Edge’s live vehicle location, fuel, health, and incident features are not represented as DT-CARGO data. |
| [Samsara GPS fleet tracking](https://www.samsara.com/products/telematics/gps-fleet-tracking) | Dashboard hierarchy and examples of organizing vehicle and trip information for operators. | GPS maps, live alerts, engine diagnostics, and dispatch are not implemented from this dataset. |
| [Fleettrack GPS tracking](https://fleettrack.in/pages/gps-tracker) | A mobile-friendly way to introduce vehicle tracking and trip-history features. | This app has no live tracker feed, geofence, or ignition state. |
| [Apple HIG: accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility), [layout](https://developer.apple.com/design/human-interface-guidelines/layout), [charts](https://developer.apple.com/design/human-interface-guidelines/charts), and [motion](https://developer.apple.com/design/human-interface-guidelines/motion) | Guidance for readable charts, responsive layouts, clear labels, touch and keyboard alternatives, and optional motion. | These are presentation principles, not a model or data source. |
| [Akter & Hernandez, “Representative truck activity patterns from anonymous mobile sensor data”](https://doi.org/10.1016/j.ijtst.2022.05.002) | Research context for describing recurring truck activity patterns from anonymized data. | It is not our training dataset or the source of our metrics. |

## 5. How to explain a result to a non-technical operator

Use this order: **what we observed → what the model noticed → what the operator should check next → what the data cannot tell us**. For example: “This recorded track has a longer near-zero-speed period than the selected group’s typical track. Check the trip schedule and surrounding records. The telemetry alone does not tell us whether the truck was loading, waiting, or stopped for another reason.”

The goal is to make the ML useful without asking an operator to interpret statistical jargon or treat a model flag as a final decision.

## Source code map

- [Home and fleet overview](../src/webapp/home.py)
- [Fleet overview](../src/webapp/overview.py)
- [Movement groups and 3D comparison](../src/webapp/cluster_analysis.py) · [3D scene](../src/webapp/cluster_3d.py)
- [Anomaly review](../src/webapp/anomaly.py)
- [Tour duration form](../src/webapp/duration.py) · [model training code](../src/tour_duration/train_model.py)
- [Recorded trip replay](../src/webapp/vehicle_sim_page.py) · [3D speed scene](../src/webapp/speed_sim_3d.py)
