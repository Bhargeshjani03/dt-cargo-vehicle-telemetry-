
import { useEffect, useMemo, useState } from "react";
import {
  getValidationSummary,
  getValidationPredictions,
  getValidationClusters,
  getErrorDistribution,
  getDurationReliability,
  getRegressionModelInfo,
} from "../../services/api/validationApi";
import "./validation.css";

const number = (value, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
};

const integer = (value) =>
  value === null || value === undefined
    ? "—"
    : Number(value).toLocaleString("en-IN");


function MetricCard({ label, value, unit, description }) {
  return (
    <div className="validation-metric-card">
      <span className="validation-metric-label">{label}</span>

      <div className="validation-metric-number">
        <strong>{value}</strong>
        {unit && <span>{unit}</span>}
      </div>

      {description && (
        <small>{description}</small>
      )}
    </div>
  );
}


function Section({ eyebrow, title, description, children }) {
  return (
    <section className="validation-section">
      <div className="validation-section-heading">
        <div>
          {eyebrow && (
            <span className="validation-eyebrow">{eyebrow}</span>
          )}
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

function ComparisonRow({ label, training, test, unit = "h" }) {
  return (
    <tr>
      <td>{label}</td>
      <td>{number(training)} {unit}</td>
      <td>{number(test)} {unit}</td>
    </tr>
  );
}

function ErrorBars({ rows }) {
  const maximum = Math.max(
    1,
    ...rows.map((item) => Number(item.count || 0))
  );

  return (
    <div className="validation-bars">
      {rows.map((item) => (
        <div className="validation-bar-row" key={item.error_range}>
          <span className="validation-bar-label">
            {item.error_range}
          </span>
          <div className="validation-bar-track">
            <div
              className="validation-bar-fill"
              style={{
                width: `${(item.count / maximum) * 100}%`,
              }}
            />
          </div>
          <strong>{integer(item.count)}</strong>
        </div>
      ))}
    </div>
  );
}


function ActualPredictedPlot({ rows }) {
  const valid = rows.filter((row) => {
    const actual = Number(row.actual_elapsed_span_hours);
    const predicted = Number(row.predicted_elapsed_span_hours);

    return (
      Number.isFinite(actual) &&
      Number.isFinite(predicted) &&
      actual >= 0 &&
      predicted >= 0
    );
  });

  if (!valid.length) {
    return (
      <div className="validation-state">
        No valid prediction records available for plotting.
      </div>
    );
  }

  const sortedValues = valid
    .flatMap((row) => [
      Number(row.actual_elapsed_span_hours),
      Number(row.predicted_elapsed_span_hours),
    ])
    .sort((a, b) => a - b);

  // Use the 98th percentile to prevent a few extreme tours
  // from compressing the majority of points into one corner.
  const percentileIndex = Math.floor(
    (sortedValues.length - 1) * 0.98
  );

  const maxValue = Math.max(1, sortedValues[percentileIndex]);

  const width = 720;
  const height = 420;

  const left = 75;
  const right = 25;
  const top = 25;
  const bottom = 65;

  const plotWidth = width - left - right;
  const plotHeight = height - top - bottom;

  const xScale = (value) =>
    left + (Math.min(value, maxValue) / maxValue) * plotWidth;

  const yScale = (value) =>
    top + plotHeight -
    (Math.min(value, maxValue) / maxValue) * plotHeight;

  const ticks = Array.from(
    { length: 6 },
    (_, index) => (maxValue * index) / 5
  );

  return (
    <div className="validation-chart-card">
      <div className="chart-legend">
        <span>
          <i className="legend-dot" />
          Held-out tour predictions
        </span>
        <span>
          <i className="legend-line" />
          Perfect prediction
        </span>
      </div>

      <div className="validation-chart-scroll">
        <svg
          className="validation-scatter"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label="Scatter plot comparing actual and predicted tour duration"
        >
          {ticks.map((tick, index) => (
            <g key={index}>
              <line
                className="chart-grid-line"
                x1={left}
                y1={yScale(tick)}
                x2={width - right}
                y2={yScale(tick)}
              />

              <line
                className="chart-grid-line"
                x1={xScale(tick)}
                y1={top}
                x2={xScale(tick)}
                y2={top + plotHeight}
              />

              <text
                className="chart-axis-label"
                x={left - 12}
                y={yScale(tick) + 4}
                textAnchor="end"
              >
                {tick.toFixed(0)}
              </text>

              <text
                className="chart-axis-label"
                x={xScale(tick)}
                y={top + plotHeight + 20}
                textAnchor="middle"
              >
                {tick.toFixed(0)}
              </text>
            </g>
          ))}

          <line
            className="ideal-prediction-line"
            x1={xScale(0)}
            y1={yScale(0)}
            x2={xScale(maxValue)}
            y2={yScale(maxValue)}
          />

          {valid.map((row, index) => {
            const actual = Number(row.actual_elapsed_span_hours);
            const predicted = Number(row.predicted_elapsed_span_hours);

            return (
              <circle
                key={`${row.tour_id}-${index}`}
                className="scatter-point"
                cx={xScale(actual)}
                cy={yScale(predicted)}
                r="3.5"
              >
                <title>
                  Tour {row.tour_id} | Actual: {actual.toFixed(2)} h |
                  Predicted: {predicted.toFixed(2)} h
                </title>
              </circle>
            );
          })}

          <line
            x1={left}
            y1={top + plotHeight}
            x2={width - right}
            y2={top + plotHeight}
            stroke="#64748b"
          />

          <line
            x1={left}
            y1={top}
            x2={left}
            y2={top + plotHeight}
            stroke="#64748b"
          />

          <text
            className="chart-axis-title"
            x={left + plotWidth / 2}
            y={height - 12}
            textAnchor="middle"
          >
            Actual elapsed span (hours)
          </text>

          <text
            className="chart-axis-title"
            transform={`translate(18 ${top + plotHeight / 2}) rotate(-90)`}
            textAnchor="middle"
          >
            Predicted elapsed span (hours)
          </text>
        </svg>
      </div>

      <p>
        Each dot represents a held-out tour. The diagonal represents
        perfect prediction. The axes use the 98th percentile of
        actual and predicted values; observations beyond this range
        are clipped to the chart boundary.
      </p>
    </div>
  );
}


function ClusterTable({ rows }) {
  return (
    <div className="validation-table-wrap">
      <table className="validation-table">
        <thead>
          <tr>
            <th>Cluster</th>
            <th>Test tours</th>
            <th>MAE (h)</th>
            <th>RMSE (h)</th>
            <th>R²</th>
            <th>MAPE</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.cluster_id}>
              <td>
                <strong>Cluster {row.cluster_id}</strong>
                <span className="validation-cell-subtitle">
                  {row.cluster_name}
                </span>
              </td>
              <td>{integer(row.sample_count)}</td>
              <td>{number(row.mae_hours)}</td>
              <td>{number(row.rmse_hours)}</td>
              <td>{number(row.r2_score, 3)}</td>
              <td>{number(row.mape_percentage)}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ReliabilityTable({ rows }) {
  return (
    <div className="validation-table-wrap">
      <table className="validation-table">
        <thead>
          <tr>
            <th>Actual tour duration</th>
            <th>Test tours</th>
            <th>MAE (h)</th>
            <th>90th percentile error (h)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.duration_range}>
              <td>{row.duration_range}</td>
              <td>{integer(row.sample_count)}</td>
              <td>{number(row.mae_hours)}</td>
              <td>{number(row.p90_absolute_error_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="validation-chart-note">
        These are retrospective error summaries grouped by actual
        duration. They are not prediction-time confidence intervals
        or guarantees for an individual tour.
      </p>
    </div>
  );
}


function ModelInformation({ info }) {
  if (!info) return null;

  const treeParams = info.decision_tree_parameters || {};
  const kmeansParams = info.kmeans_parameters || {};
  const structure = info.tree_structure || {};

  return (
    <div className="model-transparency-grid">

      {/* Model configuration */}
      <div className="model-info-card">
        <h3>Model configuration</h3>

        <dl className="model-info-list">
          <div>
            <dt>Model version</dt>
            <dd>{info.model_version || "—"}</dd>
          </div>

          <div>
            <dt>Target variable</dt>
            <dd>{info.target || "—"}</dd>
          </div>

          <div>
            <dt>Target transformation</dt>
            <dd>{info.target_transform || "—"}</dd>
          </div>

          <div>
            <dt>Clustering transformation</dt>
            <dd>{info.cluster_transform || "—"}</dd>
          </div>

          <div>
            <dt>Training rows</dt>
            <dd>{integer(info.training_rows)}</dd>
          </div>

          <div>
            <dt>Scikit-learn version</dt>
            <dd>{info.scikit_learn_version || "—"}</dd>
          </div>
        </dl>
      </div>

      {/* K-Means */}
      <div className="model-info-card">
        <h3>K-Means parameters</h3>

        <dl className="model-info-list">
          <div>
            <dt>Number of clusters</dt>
            <dd>{kmeansParams.n_clusters ?? "—"}</dd>
          </div>

          <div>
            <dt>Random state</dt>
            <dd>{kmeansParams.random_state ?? "—"}</dd>
          </div>

          <div>
            <dt>Initializations</dt>
            <dd>{kmeansParams.n_init ?? "—"}</dd>
          </div>

          <div>
            <dt>Cluster features</dt>
            <dd>{(info.cluster_features || []).join(", ")}</dd>
          </div>
        </dl>
      </div>

      {/* Decision Tree */}
      <div className="model-info-card">
        <h3>Decision Tree parameters</h3>

        <dl className="model-info-list">
          <div>
            <dt>Maximum configured depth</dt>
            <dd>{treeParams.max_depth ?? "—"}</dd>
          </div>

          <div>
            <dt>Actual fitted depth</dt>
            <dd>{structure.actual_depth ?? "—"}</dd>
          </div>

          <div>
            <dt>Minimum split samples</dt>
            <dd>{treeParams.min_samples_split ?? "—"}</dd>
          </div>

          <div>
            <dt>Minimum leaf samples</dt>
            <dd>{treeParams.min_samples_leaf ?? "—"}</dd>
          </div>

          <div>
            <dt>Leaf count</dt>
            <dd>{integer(structure.leaf_count)}</dd>
          </div>

          <div>
            <dt>Node count</dt>
            <dd>{integer(structure.node_count)}</dd>
          </div>

          <div>
            <dt>Regression features</dt>
            <dd>{(info.tree_features || []).join(", ")}</dd>
          </div>
        </dl>
      </div>

      {/* Feature importance */}
      <div className="model-info-card">
        <h3>Feature importance</h3>

        {(info.feature_importances || []).map((item) => (
          <div className="model-importance-row" key={item.feature}>
            <div className="model-importance-heading">
              <span>{item.feature}</span>
              <strong>
                {number(item.importance * 100)}%
              </strong>
            </div>

            <div className="model-importance-track">
              <div
                className="model-importance-fill"
                style={{
                  width: `${item.importance * 100}%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Cluster profiles */}
      <div className="model-info-card model-cluster-card">
        <h3>Cluster profiles from training data</h3>

        <div className="model-cluster-grid">
          {Object.entries(info.cluster_profiles || {}).map(
            ([clusterId, profile]) => (
              <div className="model-cluster-profile" key={clusterId}>
                <strong>
                  Cluster {clusterId}
                </strong>

                <span className="model-cluster-name">
                  {info.cluster_names?.[clusterId] ||
                    "Operational pattern"}
                </span>

                <div>
                  <span>Training tours</span>
                  <strong>{integer(profile.tour_count)}</strong>
                </div>

                <div>
                  <span>Median distance</span>
                  <strong>
                    {number(profile.median_distance_km)} km
                  </strong>
                </div>

                <div>
                  <span>Median speed</span>
                  <strong>
                    {number(profile.median_speed_kmh)} km/h
                  </strong>
                </div>

                <div>
                  <span>Median track count</span>
                  <strong>
                    {number(profile.median_track_count, 0)}
                  </strong>
                </div>

                <div>
                  <span>Median elapsed span</span>
                  <strong>
                    {number(profile.median_elapsed_span_hours)} h
                  </strong>
                </div>
              </div>
            )
          )}
        </div>
      </div>

    </div>
  );
}


function PredictionTable({ rows }) {
  return (
    <div className="validation-table-wrap">
      <table className="validation-table">
        <thead>
          <tr>
            <th>Tour ID</th>
            <th>Vehicle</th>
            <th>Fleet test</th>
            <th>Cluster</th>
            <th>Actual (h)</th>
            <th>Predicted (h)</th>
            <th>Absolute error (h)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.tour_id}-${index}`}>
              <td>{row.tour_id}</td>
              <td>{row.vehicle_id}</td>
              <td>{row.fleet_test_id}</td>
              <td>{row.predicted_cluster_id}</td>
              <td>{number(row.actual_elapsed_span_hours)}</td>
              <td>{number(row.predicted_elapsed_span_hours)}</td>
              <td>{number(row.absolute_error_hours)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ValidationPage() {
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [clusters, setClusters] = useState([]);
  const [errors, setErrors] = useState([]);
  const [reliability, setReliability] = useState([]);
  const [modelInfo, setModelInfo] = useState(null);

  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [
          summaryData,
          predictionData,
          clusterData,
          errorData,
          reliabilityData,
          modelData,
        ] = await Promise.all([
          getValidationSummary(),
          getValidationPredictions(page, 100),
          getValidationClusters(),
          getErrorDistribution(),
          getDurationReliability(),
          getRegressionModelInfo(),
        ]);

        if (!active) return;

        setSummary(summaryData);
        setPredictions(predictionData.records || []);
        setPagination(predictionData);
        setClusters(clusterData || []);
        setErrors(errorData || []);
        setReliability(reliabilityData || []);
        setModelInfo(modelData);
      } catch (err) {
        if (active) {
          setError(err.message || "Unable to load validation dashboard.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadDashboard();

    return () => {
      active = false;
    };
  }, [page]);

  const test = summary?.test_metrics;
  const training = summary?.training_metrics;
  const split = summary?.train_test_split;

  const testShare = useMemo(() => {
    if (!split?.train_count || !split?.test_count) return "—";

    const total = split.train_count + split.test_count;
    return `${number((split.test_count / total) * 100, 1)}%`;
  }, [split]);

  if (loading && !summary) {
    return (
      <div className="validation-page">
        <div className="validation-loading">
          Loading regression validation results…
        </div>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="validation-page">
        <div className="validation-error">
          <h2>Validation data unavailable</h2>
          <p>{error}</p>
          <p>
            Check that the backend is running and that the holdout
            validation files are present in the artifacts directory.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="validation-page">
      <header className="validation-header">
        <div>
          <span className="validation-eyebrow">
            TOUR REGRESSION · MODEL EVALUATION
          </span>
          <h1>Held-out Validation</h1>
          <p>
            Evaluation of tour-duration predictions on data excluded
            from model fitting.
          </p>
        </div>

        <div className="validation-status">
          <span className="validation-status-dot" />
          Holdout evaluation
        </div>
      </header>

      {error && (
        <div className="validation-inline-error">{error}</div>
      )}

      <div className="validation-context">
        <strong>Evaluation protocol</strong>
        <span>
          {split?.train_count?.toLocaleString("en-IN")} training tours
        </span>
        <span>
          {split?.test_count?.toLocaleString("en-IN")} test tours
        </span>
        <span>{testShare} held out</span>
        <span>Random state: {split?.random_state ?? "—"}</span>
      </div>

      <Section
        eyebrow="PRIMARY RESULT"
        title="Held-out test performance"
        description="These metrics are calculated on the 20% test split that was not used to fit preprocessing, clustering or regression."
      >
        <div className="validation-metrics-grid">
          <MetricCard
            label="Mean absolute error"
            value={number(test?.mae_hours)}
            unit="hours"
            description={`${number(
              (test?.mae_hours || 0) * 60
            )} minutes average absolute error`}
          />
          <MetricCard
            label="Root mean squared error"
            value={number(test?.rmse_hours)}
            unit="hours"
            description="Penalizes larger prediction errors"
          />
          <MetricCard
            label="Median absolute error"
            value={number(test?.median_absolute_error_hours)}
            unit="hours"
            description="Median absolute prediction error"
          />
          <MetricCard
            label="R² score"
            value={number(test?.r2_score, 3)}
            description="Variance explained on the held-out test set"
          />
          <MetricCard
            label="MAPE"
            value={number(test?.mape_percentage)}
            unit="%"
            description={`${integer(test?.mape_sample_count)} observations`}
          />
          <MetricCard
            label="Test tours"
            value={integer(test?.sample_count)}
            description="Tours in the held-out evaluation"
          />
        </div>
      </Section>

      <Section
        eyebrow="GENERALIZATION"
        title="Training versus test performance"
        description="A comparison helps show how performance changes when the model predicts tours it did not train on."
      >
        <div className="validation-panel">
          <div className="validation-table-wrap">
            <table className="validation-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Training</th>
                  <th>Test</th>
                </tr>
              </thead>
              <tbody>
                <ComparisonRow
                  label="MAE"
                  training={training?.mae_hours}
                  test={test?.mae_hours}
                />
                <ComparisonRow
                  label="RMSE"
                  training={training?.rmse_hours}
                  test={test?.rmse_hours}
                />
                <ComparisonRow
                  label="Median absolute error"
                  training={training?.median_absolute_error_hours}
                  test={test?.median_absolute_error_hours}
                />
                <ComparisonRow
                  label="R²"
                  training={training?.r2_score}
                  test={test?.r2_score}
                  unit=""
                />
                <ComparisonRow
                  label="MAPE"
                  training={training?.mape_percentage}
                  test={test?.mape_percentage}
                  unit="%"
                />
              </tbody>
            </table>
          </div>
          <p className="validation-insight">
            The held-out test metrics are the primary evidence of
            generalization. Training metrics describe fit on the data
            used to train the model.
          </p>
        </div>
      </Section>

      <div className="validation-two-column">
        <Section
          eyebrow="PREDICTION BEHAVIOUR"
          title="Actual versus predicted"
          description="A visual comparison of actual and predicted elapsed tour spans."
        >
          <div className="validation-panel">
            <ActualPredictedPlot rows={predictions} />
          </div>
        </Section>

        <Section
          eyebrow="ERROR ANALYSIS"
          title="Absolute error distribution"
          description="Number of held-out tours in each absolute-error range."
        >
          <div className="validation-panel">
            <ErrorBars rows={errors} />
          </div>
        </Section>
      </div>

      <Section
        eyebrow="SEGMENT PERFORMANCE"
        title="Cluster-wise test evaluation"
        description="Performance for test tours assigned to each cluster by the K-Means model fitted on the training split."
      >
        <div className="validation-panel">
          <ClusterTable rows={clusters} />
        </div>
      </Section>

      <Section
        eyebrow="DURATION-BASED ERROR"
        title="Error by actual tour duration"
        description="Retrospective test-set errors grouped by the actual elapsed span of each tour."
      >
        <div className="validation-panel">
          <ReliabilityTable rows={reliability} />
        </div>
      </Section>

      <Section
        eyebrow="MODEL TRANSPARENCY"
        title="Model configuration and learned parameters"
        description="Information read from the saved fitted model artifact."
      >
        <ModelInformation info={modelInfo} />
      </Section>

      <Section
        eyebrow="RECORD-LEVEL INSPECTION"
        title="Held-out tour predictions"
        description="The table is sorted by absolute prediction error, largest first."
      >
        <div className="validation-panel">
          <PredictionTable rows={predictions} />

          <div className="validation-pagination">
            <span>
              Page {pagination?.page || page} of{" "}
              {pagination?.total_pages || 1}
              {" · "}
              {integer(pagination?.total_records)} test tours
            </span>

            <div>
              <button
                type="button"
                disabled={page <= 1 || loading}
                onClick={() => setPage((current) => current - 1)}
              >
                Previous
              </button>
              <button
                type="button"
                disabled={
                  loading ||
                  page >= (pagination?.total_pages || 1)
                }
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </Section>

      <footer className="validation-footer">
        <span>DT-CARGO · Tour Regression</span>
        <span>
          Model: {summary?.model_version || "—"}
        </span>
      </footer>
    </div>
  );
}
