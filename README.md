# DT-CARGO Fleet Intelligence

A local multi-page web app for fleet activity, anomaly review, vehicle and track investigation, cluster analysis, data quality, model explanations, and tour-duration prediction.

## Run locally

```bash
npm install
npm run dev
```

Open [http://127.0.0.1:8501](http://127.0.0.1:8501). Start from the repository root so the API can find processed data under `data/` and anomaly evaluation outputs under `src/anomaly_detection/reports/`.

The React and Express analyst workspace includes Fleet Overview, Anomaly Monitoring, Vehicle Explorer, Track Explorer, Tour Duration Prediction, Behaviour Clusters, Data Quality & Insights, and Model Insights & Methodology. A local mission simulator is available as a separate illustrative view. MongoDB is optional; without `MONGODB_URI`, the API reads the processed CSV snapshot directly. The server and UI run from one local origin.

To train the duration model using the project virtual environment, run `npm run model:train`. The model uses completed-tour distance during training and treats planned distance as a documented prediction proxy.

To keep using the Python analysis workbench, run `streamlit run app.py` from the repository root.

Page actions, data joins, and model limitations are documented in [docs/APP_PAGES.md](docs/APP_PAGES.md).

For Kuberns deployment and the CI/CD/CT setup, see [MLOPS.md](MLOPS.md). The container does not include the private project data; configure a read-only Kuberns Storage credential and upload the required processed files to a private bucket.
