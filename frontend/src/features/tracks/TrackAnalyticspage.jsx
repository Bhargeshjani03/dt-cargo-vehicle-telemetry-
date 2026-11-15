import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  ZAxis,
  Legend,
} from "recharts";

import {
  getTrackSummary,
  getTrackTimeline,
  getTrackDistributions,
  getTrackClusters,
  getTrackRelationships,
  getTrackExplorer,
  getTrackDetail,
  getTrackSpeedProfile,
} from "../../services/api/trackApi";

import "./trackAnalytics.css";

/* =====================================================
   HELPERS
===================================================== */

const formatNumber = (value, digits = 1) => {
  if (
    value === null ||
    value === undefined ||
    !Number.isFinite(Number(value))
  ) {
    return "—";
  }

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
};

const formatInteger = (value) => {
  if (value === null || value === undefined) {
    return "—";
  }

  return Number(value).toLocaleString("en-IN");
};

const formatDate = (value) => {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const clusterNames = {
  0: "Active Transit",
  1: "Stop-Dominant Movement",
  2: "Brief Near-Stationary Tracks",
};

/* =====================================================
   REUSABLE COMPONENTS
===================================================== */

function MetricCard({ title, value, subtitle, icon }) {
  return (
    <div className="ta-metric-card">
      <div className="ta-metric-heading">
        <span>{title}</span>
        <span className="ta-metric-icon">{icon}</span>
      </div>

      <h2>{value}</h2>

      <p>{subtitle}</p>
    </div>
  );
}

function SectionHeader({ eyebrow, title, description }) {
  return (
    <div className="ta-section-header">
      <span className="ta-eyebrow">{eyebrow}</span>

      <h2>{title}</h2>

      {description && <p>{description}</p>}
    </div>
  );
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null;
  }

  return (
    <div className="ta-chart-tooltip">
      <strong>{label}</strong>

      {payload.map((item, index) => (
        <div key={index}>
          {item.name}: {formatNumber(item.value, 2)}
        </div>
      ))}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="ta-loading-state">
      <div className="ta-loader" />
      <p>Loading Track Analytics...</p>
    </div>
  );
}

/* =====================================================
   DISTRIBUTION CHART
===================================================== */

function DistributionChart({ title, unit, data, color = "#55b5a5" }) {
  return (
    <div className="ta-chart-card">
      <div className="ta-chart-card-header">
        <h3>{title}</h3>
        <span>{unit}</span>
      </div>

      {!data?.length ? (
        <div className="ta-empty-chart">No data available</div>
      ) : (
        <ResponsiveContainer width="100%" height={240}>
          <BarChart
            data={data}
            margin={{
              top: 15,
              right: 10,
              left: -15,
              bottom: 35,
            }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#29394c"
              vertical={false}
            />

            <XAxis
              dataKey="label"
              angle={-35}
              textAnchor="end"
              interval="preserveStartEnd"
              tick={{
                fill: "#8494a9",
                fontSize: 9,
              }}
              axisLine={{ stroke: "#34465a" }}
              tickLine={false}
            />

            <YAxis
              tick={{
                fill: "#8494a9",
                fontSize: 10,
              }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip content={<ChartTooltip />} />

            <Bar
              dataKey="count"
              name="Tracks"
              fill={color}
              radius={[4, 4, 0, 0]}
              maxBarSize={35}
            />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

/* =====================================================
   MONTHLY ACTIVITY
===================================================== */

function MonthlyActivity({ data }) {
  return (
    <div className="ta-chart-card">
      <div className="ta-chart-card-header">
        <h3>Monthly track activity</h3>
        <span>Tracks</span>
      </div>

      {!data?.length ? (
        <div className="ta-empty-chart">No timeline data available</div>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{
              top: 15,
              right: 15,
              left: -15,
              bottom: 5,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#29394c" />

            <XAxis
              dataKey="month"
              tick={{
                fill: "#8494a9",
                fontSize: 10,
              }}
              axisLine={{ stroke: "#34465a" }}
              tickLine={false}
            />

            <YAxis
              tick={{
                fill: "#8494a9",
                fontSize: 10,
              }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip content={<ChartTooltip />} />

            <Legend
              wrapperStyle={{
                color: "#aab8c9",
                fontSize: 11,
              }}
            />

            <Line
              type="monotone"
              dataKey="tracks"
              name="Total tracks"
              stroke="#62b7a7"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />

            <Line
              type="monotone"
              dataKey="scored_tracks"
              name="Scored tracks"
              stroke="#8b9de0"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

/* =====================================================
   QUALITY BREAKDOWN
===================================================== */

function QualityBreakdown({ counts, total }) {
  const entries = Object.entries(counts || {});

  const colors = ["#57b5a5", "#d6a36d", "#8497d7", "#9b86c9"];

  return (
    <div className="ta-quality-card">
      <div className="ta-chart-card-header">
        <h3>Track quality status</h3>
        <span>All original tracks</span>
      </div>

      {entries.length === 0 ? (
        <div className="ta-empty-chart">No quality information available</div>
      ) : (
        <div className="ta-quality-list">
          {entries.map(([name, count], index) => {
            const percentage = total ? (count / total) * 100 : 0;

            return (
              <div className="ta-quality-item" key={name}>
                <div className="ta-quality-item-heading">
                  <span>{name.replaceAll("_", " ")}</span>

                  <strong>{formatInteger(count)}</strong>
                </div>

                <div className="ta-quality-progress">
                  <div
                    style={{
                      width: `${percentage}%`,
                      backgroundColor: colors[index % colors.length],
                    }}
                  />
                </div>

                <small>{formatNumber(percentage)}%</small>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* =====================================================
   MOVEMENT CLUSTER CARDS
===================================================== */

function ClusterComparison({ clusters }) {
  if (!clusters?.length) {
    return (
      <div className="ta-empty-chart">No cluster information available</div>
    );
  }

  return (
    <div className="ta-cluster-grid">
      {clusters.map((cluster) => (
        <div className="ta-cluster-card" key={cluster.cluster_id}>
          <div className="ta-cluster-top">
            <span>CLUSTER {cluster.cluster_id}</span>

            <strong>{formatInteger(cluster.tracks)} tracks</strong>
          </div>

          <h3>{cluster.cluster_name}</h3>

          <p>{cluster.cluster_description}</p>

          <div className="ta-cluster-metrics">
            <div>
              <span>Median speed</span>
              <strong>
                {formatNumber(
                  cluster.median_raw_speed_kmh ?? cluster.median_avg_speed_kmh,
                )}{" "}
                km/h
              </strong>
            </div>

            <div>
              <span>Low-speed time</span>
              <strong>{formatNumber(cluster.median_low_speed_pct)}%</strong>
            </div>

            <div>
              <span>Stop episodes</span>
              <strong>{formatNumber(cluster.median_stop_episodes)}</strong>
            </div>

            <div>
              <span>Median distance</span>
              <strong>{formatNumber(cluster.median_distance_km)} km</strong>
            </div>

            <div>
              <span>Median duration</span>
              <strong>
                {formatNumber(cluster.median_duration_minutes)} min
              </strong>
            </div>

            <div>
              <span>Anomaly flagged</span>
              <strong>{formatInteger(cluster.anomaly_flagged)}</strong>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* =====================================================
   DISTANCE VS DURATION SCATTER PLOT
===================================================== */

function DistanceDurationChart({ data }) {
  const validData = useMemo(() => {
    return (data || []).filter((item) => {
      return (
        Number.isFinite(Number(item.distance_km)) &&
        Number.isFinite(Number(item.duration_minutes))
      );
    });
  }, [data]);

  const clusterData = [0, 1, 2].map((clusterId) => ({
    clusterId,

    points: validData
      .filter((item) => Number(item.cluster) === clusterId)
      .map((item) => ({
        distance: Number(item.distance_km),

        duration: Number(item.duration_minutes),
      })),
  }));

  return (
    <div className="ta-chart-card">
      <div className="ta-chart-card-header">
        <h3>Distance versus duration</h3>
        <span>Sample of up to 1,500 tracks</span>
      </div>

      {!validData.length ? (
        <div className="ta-empty-chart">No relationship data available</div>
      ) : (
        <ResponsiveContainer width="100%" height={350}>
          <ScatterChart
            margin={{
              top: 15,
              right: 20,
              bottom: 15,
              left: 10,
            }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#29394c" />

            <XAxis
              type="number"
              dataKey="distance"
              name="Distance"
              unit=" km"
              tick={{
                fill: "#8494a9",
                fontSize: 10,
              }}
              axisLine={{ stroke: "#34465a" }}
              tickLine={false}
            />

            <YAxis
              type="number"
              dataKey="duration"
              name="Duration"
              unit=" min"
              tick={{
                fill: "#8494a9",
                fontSize: 10,
              }}
              axisLine={false}
              tickLine={false}
            />

            <ZAxis range={[30, 30]} />

            <Tooltip
              cursor={{
                strokeDasharray: "3 3",
              }}
            />

            <Legend />

            <Scatter
              name="Active Transit"
              data={clusterData[0].points}
              fill="#55b5a5"
              fillOpacity={0.6}
            />

            <Scatter
              name="Stop-Dominant Movement"
              data={clusterData[1].points}
              fill="#d6a36d"
              fillOpacity={0.6}
            />

            <Scatter
              name="Brief Near-Stationary Tracks"
              data={clusterData[2].points}
              fill="#8b9de0"
              fillOpacity={0.6}
            />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

function AnomalyEvidencePanel({ evidence }) {
  if (!evidence) {
    return (
      <section className="ta-anomaly-evidence">
        <div className="ta-evidence-heading">
          <div>
            <span className="ta-eyebrow">MODEL EXPLANATION</span>
            <h3>Anomaly evidence</h3>
          </div>
          <span className="ta-evidence-badge ta-evidence-unavailable">
            Unavailable
          </span>
        </div>

        <p className="ta-evidence-note">
          Anomaly evidence is not available for this track. Check that the
          backend has been restarted with the updated track detail endpoint.
        </p>
      </section>
    );
  }

  const {
    assessment,
    anomaly_score,
    cluster_threshold,
    score_margin,
    score_to_threshold_ratio,
    cluster,
    model_version,
    features = {},
    explanation,
    interpretation_note,
  } = evidence;

  const flagged = assessment === "flagged";
  const unavailable = assessment === "unavailable";

  const featureOrder = [
    "raw_speed_mean_kmh",
    "raw_speed_std",
    "low_speed_time_pct_03",
    "stop_episode_count_03",
  ];

  const formatValue = (value, digits = 3) => {
    if (value == null || !Number.isFinite(Number(value))) {
      return "Unavailable";
    }

    return Number(value).toLocaleString("en-IN", {
      maximumFractionDigits: digits,
    });
  };

  return (
    <section className="ta-anomaly-evidence">
      <div className="ta-evidence-heading">
        <div>
          <span className="ta-eyebrow">MODEL EXPLANATION</span>
          <h3>Anomaly evidence</h3>
          <p>Track-level Isolation Forest assessment and its input features.</p>
        </div>

        <span
          className={`ta-evidence-badge ${
            unavailable
              ? "ta-evidence-unavailable"
              : flagged
                ? "ta-evidence-flagged"
                : "ta-evidence-normal"
          }`}
        >
          {unavailable
            ? "Not assessed"
            : flagged
              ? "Threshold exceeded"
              : "Within threshold"}
        </span>
      </div>

      <div className="ta-score-comparison">
        <div className="ta-score-card">
          <span>Anomaly score</span>
          <strong>{formatValue(anomaly_score, 6)}</strong>
          <small>Negative Isolation Forest decision function</small>
        </div>

        <div className="ta-score-card">
          <span>Cluster threshold</span>
          <strong>{formatValue(cluster_threshold, 6)}</strong>
          <small>Threshold applied to this movement cluster</small>
        </div>

        <div className="ta-score-card">
          <span>Score margin</span>
          <strong>
            {score_margin == null
              ? "—"
              : `${score_margin > 0 ? "+" : ""}${formatValue(score_margin, 6)}`}
          </strong>
          <small>Score minus threshold</small>
        </div>
      </div>

      <div className="ta-evidence-context">
        <span>
          Movement cluster: <strong>{cluster ?? "Unassigned"}</strong>
        </span>

        <span>
          Score / threshold:{" "}
          <strong>
            {score_to_threshold_ratio == null
              ? "—"
              : `${formatValue(score_to_threshold_ratio, 4)}×`}
          </strong>
        </span>

        <span>
          Model: <strong>{model_version || "Unavailable"}</strong>
        </span>
      </div>

      <div className="ta-evidence-feature-heading">
        <div>
          <h4>Model input features</h4>
          <p>
            Observed values supplied to the cluster-specific Isolation Forest.
          </p>
        </div>
      </div>

      <div className="ta-feature-grid">
        {featureOrder.map((key) => {
          const feature = features[key];

          return (
            <div className="ta-feature-card" key={key}>
              <span>{feature?.label || key}</span>

              <strong>
                {formatValue(feature?.value)}
                {feature?.value == null ? "" : ` ${feature?.unit || ""}`}
              </strong>

              <p>{feature?.description || "Model input feature."}</p>
            </div>
          );
        })}
      </div>

      <div className={`ta-evidence-explanation ${flagged ? "is-flagged" : ""}`}>
        <strong>Assessment</strong>
        <p>{explanation || "No assessment explanation is available."}</p>
      </div>

      <div className="ta-evidence-disclaimer">
        <strong>Attribution limitation</strong>
        <p>
          {interpretation_note ||
            "Isolation Forest evaluates the combined feature vector. Individual feature values do not establish which feature caused the prediction."}
        </p>
      </div>
    </section>
  );
}

/* =====================================================
   INDIVIDUAL TRACK MODAL
===================================================== */

function TrackDetailsModal({ trackId, onClose }) {
  const [detail, setDetail] = useState(null);

  const [speed, setSpeed] = useState(null);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function loadDetails() {
      setLoading(true);
      setError("");

      try {
        const [track, profileResult] = await Promise.allSettled([
          getTrackDetail(trackId),

          getTrackSpeedProfile(trackId),
        ]);

        if (!active) return;

        if (track.status === "rejected") {
          throw track.reason;
        }

        setDetail(track.value);

        if (profileResult.status === "fulfilled") {
          setSpeed(profileResult.value);
        } else {
          setError(
            profileResult.reason?.message || "Speed profile unavailable.",
          );
        }
      } catch (error) {
        if (active) {
          setError(error.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDetails();

    return () => {
      active = false;
    };
  }, [trackId]);

  if (!detail && loading) {
    return (
      <div className="ta-modal-overlay">
        <div className="ta-modal">
          <div className="ta-modal-loading">Loading track details...</div>
        </div>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="ta-modal-overlay">
        <div className="ta-modal">
          <button className="ta-modal-close" onClick={onClose}>
            ×
          </button>

          <p className="ta-error-message">{error || "Unable to load track."}</p>
        </div>
      </div>
    );
  }

  const detailItems = [
    ["Vehicle", detail.vehicle_id],

    ["Tour", detail.tour_id],

    ["Distance", `${formatNumber(detail.distance_km)} km`],

    ["Duration", `${formatNumber(detail.duration_minutes)} min`],

    ["Average speed", `${formatNumber(detail.avg_speed_kmh)} km/h`],

    ["Maximum speed", `${formatNumber(detail.max_speed_kmh)} km/h`],

    ["Movement cluster", detail.cluster_name],

    ["Quality status", detail.quality_status],

    ["Anomaly score", formatNumber(detail.anomaly_score, 4)],

    [
      "Anomaly flag",
      detail.anomaly_score == null
        ? "Not scored"
        : detail.is_anomaly
          ? "Flagged"
          : "Not flagged",
    ],

    ["Low-speed time", `${formatNumber(detail.low_speed_time_pct_03)}%`],

    ["Stop episodes", formatInteger(detail.stop_episode_count_03)],
  ];

  return (
    <div
      className="ta-modal-overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="ta-modal">
        <div className="ta-modal-header">
          <div>
            <span className="ta-eyebrow">TRACK INSPECTION</span>

            <h2>Track #{trackId}</h2>
          </div>

          <button className="ta-modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        <div className="ta-detail-grid">
          {detailItems.map(([label, value]) => (
            <div className="ta-detail-item" key={label}>
              <span>{label}</span>

              <strong>{value ?? "—"}</strong>
            </div>
          ))}
        </div>
        <AnomalyEvidencePanel evidence={detail.anomaly_evidence} />
        <div className="ta-modal-section">
          <div className="ta-modal-section-heading">
            <h3>Raw telemetry speed profile</h3>

            <span>
              {speed
                ? `${formatInteger(speed.observation_count)} observations`
                : "Loading telemetry"}
            </span>
          </div>

          {error && <p className="ta-warning-message">{error}</p>}

          {speed?.points?.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart
                data={speed.points}
                margin={{
                  top: 15,
                  right: 15,
                  left: -10,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#29394c" />

                <XAxis
                  dataKey="elapsed_minutes"
                  type="number"
                  tick={{
                    fill: "#8494a9",
                    fontSize: 10,
                  }}
                  name="Elapsed time"
                  unit=" min"
                />

                <YAxis
                  tick={{
                    fill: "#8494a9",
                    fontSize: 10,
                  }}
                  unit=" km/h"
                />

                <Tooltip content={<ChartTooltip />} />

                <Line
                  type="monotone"
                  dataKey="speed_kmh"
                  name="Speed"
                  stroke="#62b7a7"
                  strokeWidth={1.8}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            !error && (
              <div className="ta-empty-chart">
                No speed observations available.
              </div>
            )
          )}
        </div>

        <div className="ta-evidence-grid">
          <div>
            <h4>Quality flags</h4>

            <pre>{JSON.stringify(detail.quality_flags ?? [], null, 2)}</pre>
          </div>

          <div>
            <h4>Reason codes</h4>

            <pre>{JSON.stringify(detail.reason_codes ?? [], null, 2)}</pre>
          </div>
        </div>

        <p className="ta-modal-note">
          An anomaly flag indicates unusual movement relative to the modelled
          movement group. It does not by itself establish a vehicle fault or
          driver violation.
        </p>
      </div>
    </div>
  );
}

/* =====================================================
   MAIN TRACK ANALYTICS PAGE
===================================================== */

export default function TrackAnalyticsPage() {
  const [summary, setSummary] = useState(null);

  const [timeline, setTimeline] = useState([]);

  const [distributions, setDistributions] = useState(null);

  const [clusters, setClusters] = useState([]);

  const [relationships, setRelationships] = useState([]);

  const [loading, setLoading] = useState(true);

  const [pageError, setPageError] = useState("");

  // Track explorer state.
  const [search, setSearch] = useState("");

  const [cluster, setCluster] = useState("");

  const [quality, setQuality] = useState("");

  const [anomalyOnly, setAnomalyOnly] = useState(false);

  const [page, setPage] = useState(1);

  const [explorer, setExplorer] = useState({
    records: [],
    total_records: 0,
    total_pages: 0,
  });

  const [explorerLoading, setExplorerLoading] = useState(false);

  const [selectedTrack, setSelectedTrack] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    const trackId = searchParams.get("track_id");

    if (trackId) {
      setSelectedTrack(trackId);
    }
  }, [searchParams]);

  /* -----------------------------------------------
     LOAD DASHBOARD DATA
  ------------------------------------------------ */

  useEffect(() => {
    let active = true;

    async function loadDashboard() {
      setLoading(true);
      setPageError("");

      try {
        const [
          summaryData,
          timelineData,
          distributionData,
          clusterData,
          relationshipData,
        ] = await Promise.all([
          getTrackSummary(),

          getTrackTimeline(),

          getTrackDistributions(),

          getTrackClusters(),

          getTrackRelationships(),
        ]);

        if (!active) return;

        setSummary(summaryData);

        setTimeline(timelineData);

        setDistributions(distributionData);

        setClusters(clusterData);

        setRelationships(relationshipData);
      } catch (error) {
        if (active) {
          setPageError(error.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadDashboard();

    return () => {
      active = false;
    };
  }, []);

  /* -----------------------------------------------
     LOAD TRACK EXPLORER
  ------------------------------------------------ */

  const loadExplorer = useCallback(async () => {
    setExplorerLoading(true);

    try {
      const result = await getTrackExplorer({
        page,

        page_size: 20,

        search,

        cluster,

        quality_status: quality,

        anomaly_only: anomalyOnly,
      });

      setExplorer(result);
    } catch (error) {
      setPageError(error.message);
    } finally {
      setExplorerLoading(false);
    }
  }, [page, search, cluster, quality, anomalyOnly]);

  useEffect(() => {
    loadExplorer();
  }, [loadExplorer]);

  /* -----------------------------------------------
     QUALITY FILTER OPTIONS
  ------------------------------------------------ */

  const qualityOptions = useMemo(() => {
    return Object.keys(summary?.quality_status_counts || {}).sort();
  }, [summary]);

  /* -----------------------------------------------
     LOADING STATE
  ------------------------------------------------ */

  if (loading) {
    return <LoadingState />;
  }

  /* -----------------------------------------------
     MAIN PAGE
  ------------------------------------------------ */

  return (
    <main className="track-analytics-page">
      {/* PAGE HEADER */}

      <header className="ta-page-header">
        <div>
          <span className="ta-eyebrow">MOVEMENT INTELLIGENCE</span>

          <h1>Track Analytics</h1>

          <p>
            Explore vehicle movement, telemetry quality, track characteristics
            and operational patterns.
          </p>

          {summary?.date_min && (
            <span className="ta-date-range">
              {formatDate(summary.date_min)}
              {" — "}
              {formatDate(summary.date_max)}
            </span>
          )}
        </div>

        <div className="ta-header-badge">
          <strong>DT</strong>
          <span>TRACK DATA</span>
        </div>
      </header>

      {/* API ERROR */}

      {pageError && (
        <div className="ta-error-banner">
          <strong>API Error:</strong> {pageError}
        </div>
      )}

      {/* =================================================
         1. OVERVIEW METRICS
      ================================================= */}

      <section className="ta-metrics-grid">
        <MetricCard
          title="Total tracks"
          value={formatInteger(summary?.total_tracks)}
          subtitle="Original track records"
          icon="⌁"
        />

        <MetricCard
          title="Vehicles"
          value={formatInteger(summary?.vehicles)}
          subtitle="Unique fleet vehicles"
          icon="◉"
        />

        <MetricCard
          title="Tours"
          value={formatInteger(summary?.tours)}
          subtitle="Unique tour identifiers"
          icon="⇢"
        />

        <MetricCard
          title="Total distance"
          value={`${formatNumber(summary?.total_distance_km, 0)} km`}
          subtitle="Non-negative track distances"
          icon="↗"
        />

        <MetricCard
          title="Scored tracks"
          value={formatInteger(summary?.scored_tracks)}
          subtitle={`${formatInteger(summary?.unscored_tracks)} unscored / unassigned`}
          icon="◎"
        />
      </section>

      {/* =================================================
         2. TEMPORAL ACTIVITY AND QUALITY
      ================================================= */}

      <section className="ta-two-column">
        <div className="ta-section">
          <SectionHeader
            eyebrow="TEMPORAL COVERAGE"
            title="Track activity over time"
            description="Monthly track volume and scored track activity."
          />

          <MonthlyActivity data={timeline} />
        </div>

        <div className="ta-section">
          <SectionHeader
            eyebrow="DATA COVERAGE"
            title="Track quality"
            description="Quality distribution across the original track population."
          />

          <QualityBreakdown
            counts={summary?.quality_status_counts}
            total={summary?.total_tracks}
          />
        </div>
      </section>

      {/* =================================================
         3. MOVEMENT DISTRIBUTIONS
      ================================================= */}

      <section className="ta-section">
        <SectionHeader
          eyebrow="MOVEMENT PATTERNS"
          title="Track distributions"
          description="Explore the distribution of distance, duration, speed and stopping behaviour."
        />

        <div className="ta-distribution-grid">
          <DistributionChart
            title="Track distance"
            unit="km"
            data={distributions?.distance_km}
          />

          <DistributionChart
            title="Track duration"
            unit="minutes"
            data={distributions?.duration_minutes}
          />

          <DistributionChart
            title="Average speed"
            unit="km/h"
            data={distributions?.average_speed_kmh}
            color="#8b9de0"
          />

          <DistributionChart
            title="Maximum speed"
            unit="km/h"
            data={distributions?.maximum_speed_kmh}
            color="#d6a36d"
          />

          <DistributionChart
            title="Low-speed time"
            unit="%"
            data={distributions?.low_speed_time_pct}
            color="#a58bd1"
          />

          <DistributionChart
            title="Stop episodes"
            unit="count"
            data={distributions?.stop_episode_count}
            color="#6c9fd2"
          />
        </div>
      </section>

      {/* =================================================
         4. MOVEMENT CLUSTERS
      ================================================= */}

      <section className="ta-section">
        <SectionHeader
          eyebrow="BEHAVIOURAL SEGMENTATION"
          title="Movement cluster comparison"
          description="Comparison of the existing K-Means movement groups. These labels describe observed feature patterns, not confirmed business states."
        />

        <ClusterComparison clusters={clusters} />
      </section>

      {/* =================================================
         5. DISTANCE VS DURATION
      ================================================= */}

      <section className="ta-section">
        <SectionHeader
          eyebrow="TRACK RELATIONSHIPS"
          title="Distance versus duration"
          description="Explore how track distance and elapsed time vary across movement groups."
        />

        <DistanceDurationChart data={relationships} />
      </section>

      {/* =================================================
         6. TRACK EXPLORER
      ================================================= */}

      <section className="ta-section">
        <SectionHeader
          eyebrow="INDIVIDUAL RECORDS"
          title="Track explorer"
          description="Search by track, vehicle or tour ID. Select a track to inspect its metadata and raw speed profile."
        />

        {/* FILTERS */}

        <div className="ta-filter-bar">
          <input
            type="text"
            placeholder="Search track, vehicle or tour ID"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                loadExplorer();
              }
            }}
          />

          <select
            value={cluster}
            onChange={(event) => {
              setCluster(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All movement clusters</option>

            <option value="0">0 · Active Transit</option>

            <option value="1">1 · Stop-Dominant Movement</option>

            <option value="2">2 · Brief Near-Stationary</option>
          </select>

          <select
            value={quality}
            onChange={(event) => {
              setQuality(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All quality statuses</option>

            {qualityOptions.map((value) => (
              <option key={value} value={value}>
                {value.replaceAll("_", " ")}
              </option>
            ))}
          </select>

          <label className="ta-checkbox">
            <input
              type="checkbox"
              checked={anomalyOnly}
              onChange={(event) => {
                setAnomalyOnly(event.target.checked);
                setPage(1);
              }}
            />
            Flagged only
          </label>

          <button
            className="ta-search-button"
            onClick={() => {
              setPage(1);
              loadExplorer();
            }}
          >
            Search
          </button>
        </div>

        {/* TABLE INFORMATION */}

        <div className="ta-table-information">
          <span>
            {formatInteger(explorer.total_records)}
            {" matching tracks"}
          </span>

          <span>
            Page {page} of {Math.max(1, explorer.total_pages || 1)}
          </span>
        </div>

        {/* TRACK TABLE */}

        <div className="ta-table-wrapper">
          <table className="ta-table">
            <thead>
              <tr>
                <th>Track ID</th>

                <th>Vehicle</th>

                <th>Tour</th>

                <th>Start date</th>

                <th>Distance</th>

                <th>Duration</th>

                <th>Avg speed</th>

                <th>Movement group</th>

                <th>Quality</th>

                <th>Anomaly</th>
              </tr>
            </thead>

            <tbody>
              {explorerLoading ? (
                <tr>
                  <td colSpan="10" className="ta-table-empty">
                    Loading tracks...
                  </td>
                </tr>
              ) : explorer.records?.length ? (
                explorer.records.map((track) => (
                  <tr
                    key={track.track_id}
                    className="ta-table-row"
                    onClick={() => {
                      setSelectedTrack(track.track_id);
                    }}
                  >
                    <td>
                      <strong>#{track.track_id}</strong>
                    </td>

                    <td>{track.vehicle_id}</td>

                    <td>{track.tour_id}</td>

                    <td>{formatDate(track.start_time)}</td>

                    <td>{formatNumber(track.distance_km)} km</td>

                    <td>{formatNumber(track.duration_minutes)} min</td>

                    <td>{formatNumber(track.avg_speed_kmh)} km/h</td>

                    <td>
                      <span className="ta-cluster-pill">
                        {track.cluster_name || "Unassigned"}
                      </span>
                    </td>

                    <td>
                      {(track.quality_status || "unscored").replaceAll(
                        "_",
                        " ",
                      )}
                    </td>

                    <td>
                      {track.anomaly_score == null ? (
                        <span className="ta-muted">Not scored</span>
                      ) : track.is_anomaly ? (
                        <span className="ta-flagged">Flagged</span>
                      ) : (
                        <span className="ta-normal">Normal</span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="10" className="ta-table-empty">
                    No tracks match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* PAGINATION */}

        <div className="ta-pagination">
          <button
            disabled={page <= 1 || explorerLoading}
            onClick={() => {
              setPage((current) => current - 1);
            }}
          >
            Previous
          </button>

          <button
            disabled={page >= (explorer.total_pages || 1) || explorerLoading}
            onClick={() => {
              setPage((current) => current + 1);
            }}
          >
            Next
          </button>
        </div>
      </section>

      {/* DISCLAIMER */}

      <p className="ta-disclaimer">
        Track Analytics includes the original track population. Movement cluster
        and anomaly information are joined where predictions exist. Unscored
        tracks remain visible without fabricated labels or anomaly scores.
      </p>

      {/* TRACK DETAILS MODAL */}

      {selectedTrack !== null && (
        <TrackDetailsModal
          trackId={selectedTrack}
          onClose={() => {
            setSelectedTrack(null);

            const nextParams = new URLSearchParams(searchParams);
            nextParams.delete("track_id");

            setSearchParams(nextParams, { replace: true });
          }}
        />
      )}
    </main>
  );
}
