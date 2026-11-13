# DT-CARGO Web App Capability Map

## Product objective

Give fleet analysts and operations managers one place to review fleet activity, investigate unusual records, understand movement patterns and data quality, and estimate tour duration from information available before departure.

## Navigation

Include all eight destinations in the first app shell. Use a persistent left sidebar on desktop, grouped by the analyst's task:

```text
Overview

Investigate
  Anomaly Monitoring
  Vehicle Explorer
  Track Explorer

Plan
  Tour Duration

Understand
  Cluster Analysis
  Data Quality
  Model Insights
```

Keep the active page visible. As each data page is connected, carry the date range and fleet filter across pages; selecting a vehicle or track from a chart or table should open its explorer with the current context preserved. Every page should have one clear lead action; secondary controls stay close to the content they affect.

## Page actions

| Page | Primary user action |
|---|---|
| Fleet Overview | Choose a time period or fleet, then open a KPI or signal to investigate its contributing vehicles or tracks. |
| Anomaly Monitoring | Filter and rank flagged vehicles or tracks, then open a record for review. |
| Vehicle Explorer | Search for a vehicle and inspect its activity, cluster mix, and anomaly history. |
| Track Explorer | Find a track and inspect its speed, stops, quality warnings, and anomaly result; compare it with a typical track. |
| Tour Duration Prediction | Configure a planned tour with pre-departure inputs and request a duration estimate. |
| Cluster Analysis | Select a movement cluster and compare its distance, speed, stopping, duration, and population profile. |
| Data Quality & Insights | Filter quality issues and see which records are affected and which analyses can use them. |
| Model Insights & Methodology | Select a model and review its inputs, validation results, limitations, and interpretation guidance. |

## Capability modules and dependencies

| Module id | Responsibility | Depends on |
|---|---|---|
| `shared-foundation` | App shell, page navigation, shared filters, data loading, common table/chart patterns, and accessible visual styles | — |
| `fleet-overview` | Fleet, vehicle, track, distance, utilization, cluster, and anomaly summaries with drill-downs | `shared-foundation`; curated fleet/track/tour tables |
| `anomaly-monitoring` | Searchable anomaly queue, scores, thresholds, recurring vehicles, and record review | `shared-foundation`; scored tracks/vehicles and model metadata |
| `vehicle-explorer` | Vehicle history, activity summaries, cluster distribution, and anomaly frequency | `shared-foundation`; vehicle/tour/cluster data; anomaly results |
| `track-explorer` | Track details, speed/stop patterns, quality notes, anomaly results, and comparison | `shared-foundation`; track features; anomaly results |
| `tour-duration` | Pre-departure tour form and duration estimate with explanation | `shared-foundation`; populated pre-trip features and a model trained only on those features |
| `cluster-analysis` | Cluster descriptions, distributions, and behavioral comparisons | `shared-foundation`; cluster assignments and feature summaries |
| `data-quality` | Missingness, suspicious records, quality-flag definitions, and model eligibility | `shared-foundation`; quality reports and flag definitions |
| `model-insights` | Methodology, feature lists, validation metrics, thresholds, and limits for each model | `shared-foundation`; model artifacts and evaluation reports |

## Phased build order

1. `shared-foundation` plus all eight page shells — establish navigation, common filters, the visual language, and data-loading boundaries. Each page shows its purpose and primary action; unfinished analysis areas show an honest data/readiness state rather than fabricated metrics.
2. `fleet-overview` — deliver the first end-to-end analyst workflow and validate summary-to-detail navigation.
3. `data-quality` and `cluster-analysis` — make data eligibility and behavioral groupings interpretable.
4. `anomaly-monitoring` — connect scored records and make review actionable.
5. `vehicle-explorer` and `track-explorer` — deepen investigation from fleet signals to individual records.
6. `model-insights` — document the models and evaluation outputs used by the other pages.
7. `tour-duration` — connect the pre-departure form after a valid training dataset and model are available.

Initial implementation assumption: use Streamlit so the first app can run the repository's Python data and model code directly. Keep the page boundaries independent so the interface can move to a separate frontend later if needed.

## Prediction data readiness

The current distance-only tour model uses `total_distance_km`, which is observed for a completed tour and does not meet the pre-departure requirement unless it is replaced with a planned-distance field. The repository has a pre-trip training template, but its `planned_distance_km`, `planned_cargo_payload_kg`, and `operation_category` columns are empty in all 18,169 rows. A separate episode table has gross vehicle weight, trailer mass, and axle class for some records, but it does not provide planned distance. Do not present a prediction from these incomplete inputs as a pre-departure estimate; first populate and join the planned inputs, then retrain and evaluate chronologically.

## Design principles

Apply Apple's guidance to the web app through clear purpose, hierarchy, familiar navigation, direct language, reversible filters, visible feedback, privacy-aware data handling, and accessible charts. Keep charts focused on decision-relevant values and pair them with labels or tables so color is not the only way to read a result. Design responsively, with the analyst's wide-screen workflow as the primary layout.

References: [Apple Design Resources](https://developer.apple.com/design/resources/), [Human Interface Guidelines: Design Principles](https://developer.apple.com/design/human-interface-guidelines/design-principles/), [Sidebars](https://developer.apple.com/design/human-interface-guidelines/sidebars), and [Charts](https://developer.apple.com/design/human-interface-guidelines/charts).
