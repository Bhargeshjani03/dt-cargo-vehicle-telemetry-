
import { useCallback, useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
  PieChart,
  Pie,
  Cell,
} from "recharts";

import {
  getOperationalInsights,
} from "../../services/api/operationalInsightsApi";

import "./operationalInsightsPage.css";

function MetricCard({ label, value, description, icon }) {
  return (
    <div className="oi-metric-card">
      <div className="oi-metric-top">
        <span>{label}</span>
        <span className="oi-metric-icon">{icon}</span>
      </div>

      <div className="oi-metric-value">{value}</div>
      <div className="oi-metric-description">{description}</div>
    </div>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <section className="oi-section">
      <div className="oi-section-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
      </div>

      {children}
    </section>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="oi-tooltip">
      <strong>{label}</strong>

      {payload.map((item, index) => (
        <div key={index}>
          {item.name}:{" "}
          {typeof item.value === "number"
            ? item.value.toLocaleString(undefined, {
                maximumFractionDigits: 2,
              })
            : item.value}
        </div>
      ))}
    </div>
  );
}

function EmptyState({ message }) {
  return <div className="oi-empty-state">{message}</div>;
}

function OperationalInsightsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [minVehicleTracks, setMinVehicleTracks] = useState(30);
  const [topN, setTopN] = useState(10);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const result = await getOperationalInsights({
        minVehicleTracks,
        topN,
      });

      setData(result);
    } catch (err) {
      setError(err.message || "Unable to load operational insights.");
    } finally {
      setLoading(false);
    }
  }, [minVehicleTracks, topN]);

  useEffect(() => {
    loadInsights();
  }, [loadInsights]);

  if (loading && !data) {
    return (
      <div className="oi-page">
        <div className="oi-loading">
          Loading operational intelligence...
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="oi-page">
        <div className="oi-error">
          <h2>Unable to load operational insights</h2>
          <p>{error}</p>
          <button onClick={loadInsights}>Retry</button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const summary = data.summary || {};
  const vehicles = data.priority_vehicles || [];
  const monthly = data.monthly_trend || [];
  const clusters = data.cluster_contribution || [];
  const reasons = data.recurring_reasons || [];

  const clusterColors = ["#64748b", "#0d9488", "#8b5cf6"];

  return (
    <div className="oi-page">
      <header className="oi-header">
        <div>
          <div className="oi-eyebrow">DT-CARGO / INTELLIGENCE</div>
          <h1>Operational Insights</h1>
          <p>
            Investigate unusual movement patterns across your logistics fleet.
          </p>
        </div>

        <button
          className="oi-refresh-button"
          onClick={loadInsights}
          disabled={loading}
        >
          {loading ? "Refreshing..." : "↻ Refresh"}
        </button>
      </header>

      {error && (
        <div className="oi-inline-error">
          Could not refresh the data: {error}
        </div>
      )}

      {/* Summary metrics */}
      <div className="oi-metrics-grid">
        <MetricCard
          label="Scored Tracks"
          value={(summary.scored_tracks || 0).toLocaleString()}
          description="Tracks evaluated by anomaly models"
          icon="◉"
        />

        <MetricCard
          label="Flagged Tracks"
          value={(summary.flagged_tracks || 0).toLocaleString()}
          description="Tracks identified as statistical outliers"
          icon="⚑"
        />

        <MetricCard
          label="Overall Flag Rate"
          value={`${summary.overall_flag_rate_pct ?? 0}%`}
          description="Flagged tracks among scored tracks"
          icon="%"
        />

        <MetricCard
          label="Vehicles Analyzed"
          value={(summary.vehicles_analyzed || 0).toLocaleString()}
          description="Vehicles with scored tracks"
          icon="▣"
        />
      </div>

      {/* Vehicle filters */}
      <div className="oi-filter-panel">
        <div>
          <label htmlFor="oi-min-tracks">
            Minimum scored tracks per vehicle
          </label>

          <select
            id="oi-min-tracks"
            value={minVehicleTracks}
            onChange={(event) =>
              setMinVehicleTracks(Number(event.target.value))
            }
          >
            <option value={10}>10 tracks</option>
            <option value={30}>30 tracks</option>
            <option value={50}>50 tracks</option>
            <option value={100}>100 tracks</option>
          </select>
        </div>

        <div>
          <label htmlFor="oi-top-n">Vehicles to display</label>

          <select
            id="oi-top-n"
            value={topN}
            onChange={(event) => setTopN(Number(event.target.value))}
          >
            <option value={5}>Top 5</option>
            <option value={10}>Top 10</option>
            <option value={20}>Top 20</option>
            <option value={50}>Top 50</option>
          </select>
        </div>
      </div>

      {/* Vehicle priorities */}
      <Section
        title="Vehicle Investigation Priorities"
        subtitle="Vehicles ranked by the proportion of their scored tracks flagged as anomalies."
      >
        {vehicles.length === 0 ? (
          <EmptyState message="No vehicles meet the selected minimum track count." />
        ) : (
          <div className="oi-table-wrapper">
            <table className="oi-table">
              <thead>
                <tr>
                  <th>Vehicle ID</th>
                  <th>Scored Tracks</th>
                  <th>Flagged Tracks</th>
                  <th>Flag Rate</th>
                  <th>Review Priority</th>
                </tr>
              </thead>

              <tbody>
                {vehicles.map((vehicle) => (
                  <tr key={vehicle.vehicle_id}>
                    <td className="oi-vehicle-id">
                      #{vehicle.vehicle_id}
                    </td>

                    <td>
                      {vehicle.scored_tracks.toLocaleString()}
                    </td>

                    <td>
                      {vehicle.flagged_tracks.toLocaleString()}
                    </td>

                    <td>
                      <div className="oi-rate-cell">
                        <span>{vehicle.flag_rate_pct}%</span>
                        <div className="oi-rate-track">
                          <div
                            className="oi-rate-fill"
                            style={{
                              width: `${Math.min(
                                vehicle.flag_rate_pct,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    </td>

                    <td>
                      <span
                        className={`oi-priority oi-priority-${(
                          vehicle.review_level || "routine"
                        ).toLowerCase()}`}
                      >
                        {vehicle.review_level}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* Monthly trends */}
      <Section
        title="Monthly Anomaly Trends"
        subtitle="Compare flagged tracks with all tracks receiving anomaly scores each month."
      >
        {monthly.length === 0 ? (
          <EmptyState message="No monthly data available." />
        ) : (
          <div className="oi-chart-card">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart
                data={monthly}
                margin={{ top: 10, right: 20, left: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip content={<ChartTooltip />} />
                <Legend />

                <Line
                  type="monotone"
                  dataKey="scored_tracks"
                  name="Scored Tracks"
                  stroke="#64748b"
                  strokeWidth={2}
                  dot={false}
                />

                <Line
                  type="monotone"
                  dataKey="flagged_tracks"
                  name="Flagged Tracks"
                  stroke="#e8793b"
                  strokeWidth={2.5}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </Section>

      {/* Cluster contribution */}
      <Section
        title="Movement Cluster Contribution"
        subtitle="Compare flag rates and each cluster's share of all flagged tracks."
      >
        {clusters.length === 0 ? (
          <EmptyState message="No cluster data available." />
        ) : (
          <div className="oi-two-column">
            <div className="oi-chart-card">
              <h3>Flagged Tracks by Cluster</h3>

              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={clusters}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="cluster_name"
                    tick={{ fontSize: 10 }}
                    interval={0}
                  />
                  <YAxis />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar
                    dataKey="flagged_tracks"
                    name="Flagged Tracks"
                    radius={[6, 6, 0, 0]}
                  >
                    {clusters.map((cluster, index) => (
                      <Cell
                        key={cluster.cluster_id}
                        fill={clusterColors[index % clusterColors.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="oi-chart-card">
              <h3>Share of All Flagged Tracks</h3>

              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={clusters}
                    dataKey="share_of_all_flags_pct"
                    nameKey="cluster_name"
                    cx="50%"
                    cy="50%"
                    outerRadius={95}
                    label={({ name, value }) =>
                      `${name}: ${Number(value).toFixed(1)}%`
                    }
                  >
                    {clusters.map((cluster, index) => (
                      <Cell
                        key={cluster.cluster_id}
                        fill={clusterColors[index % clusterColors.length]}
                      />
                    ))}
                  </Pie>

                  <Tooltip content={<ChartTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {clusters.length > 0 && (
          <div className="oi-cluster-grid">
            {clusters.map((cluster) => (
              <div
                className="oi-cluster-card"
                key={cluster.cluster_id}
              >
                <div className="oi-cluster-name">
                  {cluster.cluster_name}
                </div>

                <div className="oi-cluster-description">
                  {cluster.cluster_description}
                </div>

                <div className="oi-cluster-stat">
                  <strong>{cluster.flag_rate_pct}%</strong>
                  <span>Flag rate</span>
                </div>

                <div className="oi-cluster-stat">
                  <strong>
                    {cluster.share_of_all_flags_pct}%
                  </strong>
                  <span>Share of flags</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Recurring reasons */}
      <Section
        title="Recurring Anomaly Reasons"
        subtitle="Most frequent reason codes among tracks flagged by the anomaly models."
      >
        {reasons.length === 0 ? (
          <EmptyState message="No reason codes were found among flagged tracks." />
        ) : (
          <div className="oi-reasons-list">
            {reasons.map((reason, index) => (
              <div className="oi-reason-row" key={reason.reason_code}>
                <div className="oi-reason-rank">
                  {index + 1}
                </div>

                <div className="oi-reason-content">
                  <strong>{reason.reason_code}</strong>
                  <div className="oi-reason-bar">
                    <div
                      style={{
                        width: `${Math.min(
                          reason.share_of_flagged_tracks_pct,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                <div className="oi-reason-count">
                  <strong>{reason.flagged_tracks}</strong>
                  <span>
                    {reason.share_of_flagged_tracks_pct}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <div className="oi-disclaimer">
        <strong>Analytical interpretation</strong>
        <p>
          These insights are based on track-level statistical anomaly
          detection. A flagged track is an unusual movement pattern
          relative to its assigned cluster. It does not establish a
          vehicle fault, driver error, or operational incident.
          Vehicle rankings are descriptive investigation priorities,
          not validated risk classifications.
        </p>
      </div>

      <div className="oi-footer">
        DT-CARGO · Track-level operational intelligence
      </div>
    </div>
  );
}

export default OperationalInsightsPage;
