
# DT-CARGO — Vehicle Telemetry Intelligence Platform

DT-CARGO is a vehicle telemetry intelligence platform designed to analyse fleet movement patterns, identify statistically unusual track-level behaviour, and estimate tour elapsed duration using machine learning.

The platform combines data preprocessing, movement clustering, anomaly detection, tour-level regression and interactive dashboards to support fleet-operation analysis.

## Available app interfaces

This branch contains the React and FastAPI dashboard described below, as well as the Streamlit analysis workbench. To run the Streamlit workbench from the repository root, use `streamlit run app.py`.

For the Streamlit page map, see [docs/APP_PAGES.md](docs/APP_PAGES.md). For a step-by-step explanation of the data, model choices, limitations, references, and simulations, see the [Project Walkthrough](docs/PROJECT_WALKTHROUGH.md).

## Overview

DT-CARGO processes vehicle tracking data at two distinct analytical levels:

- **Track-level analysis:** Groups individual tracks by movement characteristics and identifies statistically unusual tracks using cluster-specific Isolation Forest models.
- **Tour-level analysis:** Aggregates tracks into tours, performs tour clustering and estimates elapsed tour duration using Decision Tree regression.

The platform provides an interactive interface for exploring tracks, investigating vehicles, understanding anomaly evidence and reviewing model validation results.

## Key Features

### 1. Fleet Overview
- Dataset summary and fleet test distribution.
- Vehicle, track and tour statistics.
- Dataset temporal coverage.
- Analytics pipeline overview.

### 2. Anomaly Intelligence
- Track-level anomaly detection results.
- Cluster-specific anomaly thresholds.
- Flagged-track exploration.
- Anomaly score and flag-rate summaries.

### 3. Operational Insights
- Vehicle-level aggregation of track anomaly results.
- Investigation priority summaries.
- Monthly anomaly trends.
- Movement-cluster contribution.
- Recurring statistical patterns.

Vehicle-level summaries aggregate track-level predictions. DT-CARGO does not use a separate vehicle-level anomaly detection model.

### 4. Vehicle Intelligence
- Searchable vehicle directory.
- Vehicle specifications.
- Track-level anomaly history by vehicle.
- Movement-cluster distribution.
- Monthly track activity.
- Vehicle-specific track history and investigation.

### 5. Track Analytics
- Track-level metadata and movement characteristics.
- Raw telemetry speed profiles.
- Track quality information.
- Anomaly evidence panel.
- Individual track inspection.

The anomaly evidence panel presents the model score, cluster-specific threshold and the four model input feature values. It does not claim causal feature attribution.

### 6. Tour Regression
- Tour-level clustering.
- Tour elapsed-span predictions.
- Actual versus predicted duration.
- Regression validation metrics.
- Prediction error analysis.

### 7. Project Methodology
- Exploratory Data Analysis.
- Data Preprocessing.
- Movement and Tour Clustering.
- Model Development.
- Model Evaluation.
- Data Quality Assessment.

## Technology Stack

### Frontend
- React 19
- Vite
- React Router
- Recharts
- Lucide React
- CSS

### Backend
- Python
- FastAPI
- Uvicorn
- Pandas
- NumPy
- Scikit-learn
- Joblib

### Machine Learning
- K-Means Clustering
- Isolation Forest
- Decision Tree Regression

## System Architecture

```text
                    DT-CARGO
                       |
              Raw Vehicle Data
                       |
               Preprocessing
                       |
              Quality Assessment
                       |
             Feature Engineering
                       |
             +---------+---------+
             |                   |
       TRACK-LEVEL           TOUR-LEVEL
        ANALYSIS              ANALYSIS
             |                   |
      Movement K-Means      Tour Aggregation
             |                   |
      3 Movement Clusters   Tour K-Means
             |                   |
      Cluster-specific     Decision Tree
      Isolation Forest      Regression
             |                   |
      Anomaly Scores       Duration Estimates
             |                   |
             +---------+---------+
                       |
                FastAPI Backend
                       |
                 React Frontend
                       |
              DT-CARGO Dashboard
```

## Dataset Description

The project dataset contains:

| Dataset characteristic | Value |
|---|---:|
| Track records | 151,598 |
| Unique vehicles | 163 |
| Unique tour identifiers | 13,444 |
| Fleet test groups | 6 |
| Vehicles with fleet specifications | 149 |

### Data Sources

**Track metadata**

Contains track identifiers, vehicle and tour identifiers, timestamps, distance, speed summaries and operational context fields.

**Fleet specifications**

Contains vehicle configuration information, including:

- `gross_vehicle_weight`
- `total_mass_with_trailer`
- `axle_class`

**Raw speed telemetry**

Individual track files contain timestamped speed observations and HDOP information.

### Temporal Coverage

The dataset contains two major observation periods:

- August 2021 – October 2022: 126,950 tracks (83.7%).
- September 2023 – February 2024: 24,648 tracks (16.3%).

The data is episodic rather than continuously collected. Gaps between collection periods should not automatically be interpreted as missing vehicle activity.

## Machine Learning Methodology

### 1. Track Movement Clustering

K-Means is used to group individual tracks according to four telemetry-derived features:

1. `raw_speed_mean_kmh`
2. `raw_speed_std`
3. `low_speed_time_pct_03`
4. `stop_episode_count_03`

The resulting movement clusters have descriptive interpretations:

| Cluster | Descriptive label |
|---|---|
| 0 | Active Transit |
| 1 | Stop-Dominant Movement |
| 2 | Brief Near-Stationary Tracks |

These labels describe observed cluster characteristics and are not independently verified operational states.

### 2. Track-Level Anomaly Detection

Three separate Isolation Forest models are used, one for each movement cluster.

| Configuration | Value |
|---|---:|
| Algorithm | Isolation Forest |
| Number of models | 3 |
| Estimators per model | 300 |
| Input features | 4 |

Each model uses its own anomaly threshold.

| Cluster | Threshold |
|---|---:|
| 0 | 0.106925 |
| 1 | 0.165261 |
| 2 | 0.190944 |

The anomaly score is calculated as the negative Isolation Forest `decision_function`.

A higher score indicates a more unusual observation relative to the learned reference patterns.

The anomaly score is not a probability.

### 3. Tour-Level Clustering and Regression

A separate tour-level workflow aggregates track records by `tour_id`.

Tour clustering uses aggregated characteristics such as:

- `total_distance_km`
- `mean_track_speed_kmh`
- `max_track_speed_kmh`
- `track_count` (optional feature)

A Decision Tree Regressor estimates `elapsed_span_hours`.

Model configuration:

| Parameter | Value |
|---|---:|
| Maximum depth | 10 |
| Minimum samples split | 10 |
| Minimum samples leaf | 5 |
| Random state | 42 |

The target is transformed using `log1p` for modelling and converted back using `expm1` for predictions.

## Model Evaluation Results

### Track-Level Anomaly Inference

| Metric | Result |
|---|---:|
| Total original tracks | 151,598 |
| Scored tracks | 148,359 |
| Unscored / unassigned tracks | 3,239 |
| Flagged tracks | 4,185 |
| Flag rate among scored tracks | 2.82% |
| Reported processing errors | 0 |

The flag rate represents the proportion of scored tracks exceeding their respective cluster thresholds.

### Inference Parity

The inference parity evaluation tested 29,673 tracks.

- Exact flag agreement was observed.
- Score differences were effectively zero.

This verifies inference consistency, not anomaly detection accuracy against ground-truth labels.

### Tour Regression Validation

The regression model was evaluated using an 80:20 random train-test split.

| Metric | Test result |
|---|---:|
| Training tours | 6,050 |
| Test tours | 1,513 |
| MAE | 1.816 hours |
| RMSE | 6.455 hours |
| Median absolute error | 0.542 hours |
| R² | 0.868 |
| MAPE | 22.38% |

The random split evaluates held-out tours. Vehicles may occur in both training and test sets, so this should not be interpreted as unseen-vehicle generalisation.

## Project Structure

The following is a conceptual overview. Actual file locations may differ depending on the repository organisation.

```text
DT-CARGO/
│
├── backend/
│   ├── main.py
│   ├── track_analytics_api.py
│   ├── vehicle_intelligence_api.py
│   ├── validation_api.py
│   ├── data/
│   └── ...
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   │   ├── anomalies/
│   │   │   ├── insights/
│   │   │   ├── methodology/
│   │   │   ├── regression/
│   │   │   ├── tracks/
│   │   │   └── vehicles/
│   │   ├── services/
│   │   └── ...
│   ├── package.json
│   └── ...
│
├── data/
│   └── raw/
│       ├── tracks/
│       ├── speed/
│       └── fleets/
│
├── src/
│   └── tour_regression/
│       └── artifacts/
│
├── requirements.txt
├── LICENSE
├── README.md
└── .gitignore
```

## Installation and Setup

### Prerequisites

- Python 3.10 or later (use the version supported by your installed dependencies).
- Node.js and npm.
- Git.

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd DT-CARGO
```

### 2. Set up the backend

Create and activate a virtual environment:

```bash
python -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend API:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 3. Set up the frontend

Open a separate terminal:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will be available at the Vite address shown in the terminal, normally:

```text
http://localhost:5173
```

### 4. Build the frontend

To verify the production build:

```bash
cd frontend
npm run build
```

## Data and Model Artifacts

The application requires its corresponding dataset files and trained model artifacts.

The raw telemetry dataset and trained model artifacts may not be included in every repository distribution.

Ensure that the required data files and model artifacts are available at the paths expected by the backend before starting the application.

Do not commit private, restricted or excessively large datasets without permission.

## Limitations

DT-CARGO is an analytical decision-support platform. Its results should be interpreted within the limitations of the available data and modelling methodology.

- Anomaly flags identify statistically unusual tracks, not confirmed mechanical faults or driver violations.
- Isolation Forest does not provide direct causal feature attribution.
- The anomaly detection workflow operates at track level.
- Vehicle-level dashboards aggregate track-level predictions; they do not use a separate vehicle anomaly model.
- Tour regression estimates elapsed tour span and is not an anomaly detection model.
- Some tours contain multiple vehicles.
- Uneven and episodic data collection limits temporal interpretations.
- Missing vehicle specifications should not be blindly imputed.
- Ground-truth operational incident labels and analyst adjudications were not available for independent anomaly detection accuracy evaluation.

## Future Scope

Potential extensions include:

- Analyst feedback and anomaly adjudication.
- Integration with verified operational incident records.
- Unseen-vehicle validation for tour regression.
- Additional telemetry quality diagnostics.
- Model monitoring and version comparison.
- More detailed operational investigation workflows.

## Academic Project

**Project:** DT-CARGO — Vehicle Telemetry Analysis for Improving Efficiency in Logistics Fleet Operations.

This project demonstrates the application of data engineering, exploratory analysis, machine learning and interactive visualisation to fleet telemetry data.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
