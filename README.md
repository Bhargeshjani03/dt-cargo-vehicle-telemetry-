# DT-CARGO Fleet Intelligence

A local multi-page web app for fleet activity, anomaly review, vehicle and track investigation, cluster analysis, data quality, model explanations, and tour-duration prediction.

## Run locally

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Start from the repository root so the app can find processed data under `data/` and anomaly evaluation outputs under `src/anomaly_detection/reports/`.

The first working page is Fleet Overview. The other seven destinations are present in the navigation and will be filled in phases. Tour Duration remains a readiness state until populated pre-departure training inputs are available; the current regression baseline uses completed-tour distance.

Uploaded or loaded data is processed by the local app and is not sent to an external service.
