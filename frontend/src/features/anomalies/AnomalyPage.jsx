
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  Search,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  X,
} from "lucide-react";

import { anomalyApi } from "../../services/api/anomalyApi";
import "./anomaly.css";

const formatNumber = (value) =>
  Number(value || 0).toLocaleString("en-IN");

const formatScore = (value) => {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  return Number(value).toFixed(5);
};

const CLUSTER_OPTIONS = [
  { value: "", label: "All clusters" },
  { value: "0", label: "Cluster 0 · Active Transit" },
  { value: "1", label: "Cluster 1 · Stop-Dominant" },
  { value: "2", label: "Cluster 2 · Near-Stationary" },
];

function StatCard({ label, value, detail, icon: Icon, tone = "" }) {
  return (
    <div className="anomaly-stat-card">
      <div className="anomaly-stat-heading">
        <span>{label}</span>
        <div className={`anomaly-stat-icon ${tone}`}>
          <Icon size={19} />
        </div>
      </div>

      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function SectionHeader({ title, description, action }) {
  return (
    <div className="anomaly-section-header">
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

function LoadingState({ message = "Loading anomaly intelligence..." }) {
  return (
    <div className="anomaly-state">
      <RefreshCw className="anomaly-spin" size={22} />
      <span>{message}</span>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="anomaly-error">
      <AlertTriangle size={22} />
      <div>
        <strong>Unable to load anomaly data</strong>
        <p>{message}</p>
        <button onClick={onRetry}>Retry</button>
      </div>
    </div>
  );
}

/* -----------------------------------------
   CLUSTER ANALYSIS
----------------------------------------- */

function ClusterAnalysis({ clusters }) {
  return (
    <section className="anomaly-panel">
      <SectionHeader
        title="Movement cluster intelligence"
        description="Anomaly flag rates within each movement cluster."
      />

      <div className="cluster-list">
        {clusters.map((cluster) => (
          <div className="cluster-item" key={cluster.cluster_id}>
            <div className="cluster-heading">
              <div>
                <span className="cluster-id">
                  CLUSTER {cluster.cluster_id}
                </span>

                <h3>{cluster.cluster_name}</h3>
                <p>{cluster.cluster_description}</p>
              </div>

              <div className="cluster-rate">
                <strong>{cluster.flag_rate_pct}%</strong>
                <span>Flag rate</span>
              </div>
            </div>

            <div
              className="cluster-bar"
              title={`${cluster.flag_rate_pct}% flagged`}
            >
              <div
                className="cluster-bar-flagged"
                style={{
                  width: `${cluster.flag_rate_pct}%`,
                }}
              />
            </div>

            <div className="cluster-metrics">
              <span>{formatNumber(cluster.tracks)} tracks</span>
              <span>
                {formatNumber(cluster.flagged_tracks)} flagged
              </span>
              <span>
                Threshold: {formatScore(cluster.threshold)}
              </span>
            </div>

            <div className="cluster-features">
              <div>
                <small>Median speed</small>
                <strong>
                  {Number(cluster.median_speed_kmh).toFixed(2)} km/h
                </strong>
              </div>

              <div>
                <small>Low-speed time</small>
                <strong>
                  {Number(cluster.median_low_speed_pct).toFixed(1)}%
                </strong>
              </div>

              <div>
                <small>Stop episodes</small>
                <strong>
                  {Number(cluster.median_stop_episodes).toFixed(0)}
                </strong>
              </div>
            </div>
          </div>
        ))}
      </div>

      <p className="anomaly-footnote">
        Each movement cluster has its own Isolation Forest model
        and threshold. Compare flag rates within clusters rather
        than comparing raw anomaly scores across models.
      </p>
    </section>
  );
}

/* -----------------------------------------
   MONTHLY TREND
----------------------------------------- */

function MonthlyTrend({ monthly }) {
  const maxRate = Math.max(
    1,
    ...monthly.map((item) => Number(item.flag_rate_pct || 0))
  );

  return (
    <section className="anomaly-panel">
      <SectionHeader
        title="Monthly anomaly trend"
        description="Percentage of scored tracks flagged in each month."
      />

      {monthly.length === 0 ? (
        <p className="anomaly-muted">No monthly data available.</p>
      ) : (
        <>
          <div className="monthly-chart">
            {monthly.map((item) => (
              <div className="monthly-column" key={item.month}>
                <div className="monthly-bar-area">
                  <div
                    className="monthly-bar"
                    style={{
                      height: `${Math.max(
                        2,
                        (Number(item.flag_rate_pct) / maxRate) * 100
                      )}%`,
                    }}
                    title={`${item.month}: ${item.flag_rate_pct}%`}
                  />
                </div>

                <span>{item.month.slice(2)}</span>
              </div>
            ))}
          </div>

          <div className="monthly-legend">
            <span>
              <i />
              Monthly flag rate
            </span>
            <span>{monthly.length} observed months</span>
          </div>
        </>
      )}
    </section>
  );
}


function DetectionMethodology() {
  const clusterThresholds = [
    {
      cluster: "Cluster 0",
      name: "Active Transit",
      threshold: "0.106925",
    },
    {
      cluster: "Cluster 1",
      name: "Stop-Dominant Movement",
      threshold: "0.165261",
    },
    {
      cluster: "Cluster 2",
      name: "Brief Near-Stationary Tracks",
      threshold: "0.190944",
    },
  ];

  return (
    <section className="methodology-section">
      <div className="methodology-header">
        <div>
          <h2>Detection Methodology & Thresholds</h2>
          <p>
            Understand how DT-CARGO identifies stop episodes
            and unusual vehicle movement patterns.
          </p>
        </div>
        <span className="methodology-tag">
          MODEL CONFIGURATION
        </span>
      </div>

      <div className="methodology-grid">
        {/* Stop Episode Definition */}
        <div className="methodology-card">
          <div className="methodology-card-heading">
            <div className="methodology-icon stop-icon">01</div>
            <div>
              <h3>Stop Episode Detection</h3>
              <span>Movement feature extraction</span>
            </div>
          </div>

          <p className="methodology-description">
            A stop episode is counted when a continuous
            low-speed period satisfies all three conditions.
          </p>

          <div className="threshold-list">
            <div className="threshold-row">
              <span>Low-speed threshold</span>
              <strong>≤ 0.3 m/s</strong>
            </div>
            <div className="threshold-row">
              <span>Maximum observation gap</span>
              <strong>2 seconds</strong>
            </div>
            <div className="threshold-row">
              <span>Minimum stop duration</span>
              <strong>30 seconds</strong>
            </div>
          </div>

          <div className="methodology-note">
            Low-speed observations lasting less than 30 seconds
            are not counted as stop episodes.
          </div>
        </div>

        {/* Anomaly Detection */}
        <div className="methodology-card">
          <div className="methodology-card-heading">
            <div className="methodology-icon anomaly-icon">02</div>
            <div>
              <h3>Anomaly Detection</h3>
              <span>Cluster-specific Isolation Forest</span>
            </div>
          </div>

          <p className="methodology-description">
            DT-CARGO uses a separate Isolation Forest model
            for each movement cluster.
          </p>

          <div className="model-config">
            <div>
              <span>Algorithm</span>
              <strong>Isolation Forest</strong>
            </div>
            <div>
              <span>Estimators per model</span>
              <strong>300 trees</strong>
            </div>
            <div>
              <span>Threshold calibration</span>
              <strong>98th percentile</strong>
            </div>
          </div>

          <div className="methodology-note">
            Each cluster has its own threshold, derived from
            validation anomaly scores.
          </div>
        </div>
      </div>

      {/* Cluster-specific thresholds */}
      <div className="threshold-table-card">
        <div className="threshold-table-header">
          <div>
            <h3>Cluster-Specific Anomaly Thresholds</h3>
            <p>
              A track is flagged when its anomaly score exceeds
              the threshold of its assigned cluster.
            </p>
          </div>
        </div>

        <div className="threshold-table">
          <div className="threshold-table-row threshold-table-labels">
            <span>Movement cluster</span>
            <span>Model</span>
            <span>Anomaly threshold</span>
          </div>

          {clusterThresholds.map((item) => (
            <div className="threshold-table-row" key={item.cluster}>
              <div>
                <strong>{item.cluster}</strong>
                <span className="threshold-cluster-name">
                  {item.name}
                </span>
              </div>
              <span className="model-name">Isolation Forest</span>
              <strong className="threshold-value">
                {item.threshold}
              </strong>
            </div>
          ))}
        </div>
      </div>

      {/* Score interpretation */}
      <div className="score-interpretation">
        <div className="score-interpretation-title">
          <span>i</span>
          <strong>How to interpret anomaly scores</strong>
        </div>
        <p>
          Anomaly score = negative Isolation Forest decision_function.
          Higher scores indicate more unusual movement behaviour.
          A track is flagged when its score exceeds its cluster-specific
          threshold. An anomaly flag indicates statistical unusualness,
          not necessarily a vehicle fault or operational violation.
        </p>
      </div>
    </section>
  );
}

/* -----------------------------------------
   VEHICLE REVIEW
----------------------------------------- */

function VehicleReview({ vehicles }) {
  return (
    <section className="anomaly-panel">
      <SectionHeader
        title="Vehicle review candidates"
        description="Vehicles ranked by flagged track count."
      />

      <div className="anomaly-table-wrap">
        <table className="anomaly-table">
          <thead>
            <tr>
              <th>Vehicle</th>
              <th>Tracks</th>
              <th>Flagged</th>
              <th>Flag rate</th>
            </tr>
          </thead>

          <tbody>
            {vehicles.map((vehicle) => (
              <tr key={vehicle.vehicle_id}>
                <td>
                  <strong>Vehicle {vehicle.vehicle_id}</strong>
                </td>
                <td>{formatNumber(vehicle.tracks)}</td>
                <td>{formatNumber(vehicle.flagged_tracks)}</td>
                <td>
                  <span className="vehicle-rate">
                    {vehicle.flag_rate_pct}%
                  </span>
                </td>
              </tr>
            ))}

            {vehicles.length === 0 && (
              <tr>
                <td colSpan="4" className="empty-table">
                  No vehicle records available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="anomaly-footnote">
        These are statistical review candidates, not confirmed
        vehicle faults. Interpret rates alongside track counts
        and operating context.
      </p>
    </section>
  );
}

/* -----------------------------------------
   TRACK DETAIL MODAL
----------------------------------------- */

function TrackDetailsModal({ track, onClose }) {
  if (!track) return null;

  const fields = [
    ["Vehicle", track.vehicle_id],
    ["Movement cluster", track.cluster_name],
    ["Quality status", track.quality_status],
    ["Anomaly score", formatScore(track.anomaly_score)],
    ["Model threshold", formatScore(track.threshold)],
    [
      "Mean speed",
      track.raw_speed_mean_kmh == null
        ? "—"
        : `${Number(track.raw_speed_mean_kmh).toFixed(2)} km/h`,
    ],
    [
      "Speed standard deviation",
      track.raw_speed_std == null
        ? "—"
        : Number(track.raw_speed_std).toFixed(2),
    ],
    [
      "Low-speed time",
      track.low_speed_time_pct_03 == null
        ? "—"
        : `${Number(track.low_speed_time_pct_03).toFixed(2)}%`,
    ],
    ["Stop episodes", track.stop_episode_count_03 ?? "—"],
  ];

  return (
    <div className="track-modal-backdrop" onClick={onClose}>
      <div
        className="track-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="track-modal-header">
          <div>
            <span>TRACK INVESTIGATION</span>
            <h3>Track #{track.track_id}</h3>
          </div>

          <button onClick={onClose} aria-label="Close track details">
            <X size={19} />
          </button>
        </div>

        <div className="track-detail-grid">
          {fields.map(([label, value]) => (
            <div key={label}>
              <small>{label}</small>
              <strong>{value ?? "—"}</strong>
            </div>
          ))}
        </div>

        <div
          className={
            track.is_anomaly
              ? "track-detail-status flagged"
              : "track-detail-status normal"
          }
        >
          {track.is_anomaly ? (
            <AlertTriangle size={17} />
          ) : (
            <CheckCircle2 size={17} />
          )}

          {track.is_anomaly
            ? "Flagged for analyst review"
            : "Not flagged by the model"}
        </div>

        {track.start_time && (
          <p className="track-detail-time">
            Track start: {new Date(track.start_time).toLocaleString()}
          </p>
        )}

        <p className="anomaly-footnote">
          An anomaly flag indicates unusual model behaviour.
          It is not proof of a mechanical fault, driver issue
          or operational incident.
        </p>
      </div>
    </div>
  );
}

/* -----------------------------------------
   TRACK EXPLORER
----------------------------------------- */

function TrackExplorer() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [cluster, setCluster] = useState("");
  const [quality, setQuality] = useState("");
  const [anomalyOnly, setAnomalyOnly] = useState(true);
  const [page, setPage] = useState(1);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedTrack, setSelectedTrack] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadTracks() {
      setLoading(true);
      setError("");

      try {
        const result = await anomalyApi.getTracks({
          page,
          page_size: 15,
          search,
          cluster,
          quality_status: quality,
          anomaly_only: anomalyOnly,
        });

        if (!cancelled) {
          setData(result);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTracks();

    return () => {
      cancelled = true;
    };
  }, [page, search, cluster, quality, anomalyOnly]);

  function submitSearch(event) {
    event.preventDefault();
    setPage(1);
    setSearch(searchInput.trim());
  }

  async function openTrack(trackId) {
    setDetailLoading(true);
    setSelectedTrack(null);
    setError("");

    try {
      const result = await anomalyApi.getTrack(trackId);
      setSelectedTrack(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <section className="anomaly-panel">
      <SectionHeader
        title="Track investigation"
        description="Search individual tracks and inspect anomaly scores and movement features."
      />

      <form className="track-filters" onSubmit={submitSearch}>
        <div className="track-search">
          <Search size={17} />

          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search track ID or vehicle ID"
          />
        </div>

        <select
          value={cluster}
          onChange={(event) => {
            setCluster(event.target.value);
            setPage(1);
          }}
        >
          {CLUSTER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          value={quality}
          onChange={(event) => {
            setQuality(event.target.value);
            setPage(1);
          }}
        >
          <option value="">All quality statuses</option>
          <option value="eligible">Eligible</option>
          <option value="eligible_with_warnings">
            Eligible with warnings
          </option>
        </select>

        <label className="anomaly-checkbox">
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

        <button className="filter-submit" type="submit">
          Search
        </button>
      </form>

      {error && <div className="inline-error">{error}</div>}

      {loading ? (
        <LoadingState message="Loading tracks..." />
      ) : (
        <>
          <div className="anomaly-table-wrap">
            <table className="anomaly-table">
              <thead>
                <tr>
                  <th>Track ID</th>
                  <th>Vehicle</th>
                  <th>Movement cluster</th>
                  <th>Anomaly score</th>
                  <th>Threshold</th>
                  <th>Quality</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {data?.records?.map((track) => (
                  <tr key={track.track_id}>
                    <td>#{track.track_id}</td>
                    <td>{track.vehicle_id}</td>

                    <td>
                      <span className="cluster-chip">
                        {track.cluster_name}
                      </span>
                    </td>

                    <td className="score-cell">
                      {formatScore(track.anomaly_score)}
                    </td>

                    <td>{formatScore(track.threshold)}</td>
                    <td>{track.quality_status || "—"}</td>

                    <td>
                      <span
                        className={
                          track.is_anomaly
                            ? "flag-status"
                            : "normal-status"
                        }
                      >
                        {track.is_anomaly ? "Flagged" : "Normal"}
                      </span>
                    </td>

                    <td>
                      <button
                        className="view-track"
                        onClick={() => openTrack(track.track_id)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}

                {data?.records?.length === 0 && (
                  <tr>
                    <td colSpan="8" className="empty-table">
                      No tracks match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="table-pagination">
            <span>
              {formatNumber(data?.total_records || 0)} matching tracks
            </span>

            <div>
              <button
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
                aria-label="Previous page"
              >
                <ChevronLeft size={16} />
              </button>

              <span>
                Page {data?.page || 1} of {data?.total_pages || 1}
              </span>

              <button
                disabled={page >= (data?.total_pages || 1)}
                onClick={() => setPage((current) => current + 1)}
                aria-label="Next page"
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </>
      )}

      {detailLoading && (
        <div className="track-modal-backdrop">
          <div className="track-modal">
            <LoadingState message="Loading track details..." />
          </div>
        </div>
      )}

      <TrackDetailsModal
        track={selectedTrack}
        onClose={() => setSelectedTrack(null)}
      />
    </section>
  );
}

/* -----------------------------------------
   MAIN PAGE
----------------------------------------- */

export default function AnomalyPage() {
  const [summary, setSummary] = useState(null);
  const [clusters, setClusters] = useState([]);
  const [monthly, setMonthly] = useState([]);
  const [vehicles, setVehicles] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setLoading(true);
    setError("");

    try {
      const [
        summaryData,
        clusterData,
        monthlyData,
        vehicleData,
      ] = await Promise.all([
        anomalyApi.getSummary(),
        anomalyApi.getClusters(),
        anomalyApi.getMonthly(),
        anomalyApi.getVehicles(10),
      ]);

      setSummary(summaryData);
      setClusters(clusterData);
      setMonthly(monthlyData);
      setVehicles(vehicleData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  if (loading) {
    return <LoadingState />;
  }

  if (error && !summary) {
    return (
      <ErrorState
        message={error}
        onRetry={loadDashboard}
      />
    );
  }

  if (!summary) return null;

  return (
    <div className="anomaly-page">
      <div className="anomaly-page-intro">
        <div>
          <span className="eyebrow">
            TRACK-LEVEL MACHINE LEARNING
          </span>

          <h1>Anomaly Intelligence</h1>

          <p>
            Identify unusual vehicle movement patterns using
            cluster-specific Isolation Forest models.
          </p>
        </div>

        <button
          className="refresh-dashboard"
          onClick={loadDashboard}
        >
          <RefreshCw size={15} />
          Refresh data
        </button>
      </div>

      {error && <div className="inline-error">{error}</div>}

      <div className="anomaly-model-banner">
        <div className="model-banner-icon">
          <Activity size={21} />
        </div>

        <div>
          <strong>
            DT-CARGO v2.0 · Cluster-aware anomaly detection
          </strong>

          <p>
            Three movement clusters, each evaluated using its own
            Isolation Forest model and threshold.
          </p>
        </div>
      </div>

      <div className="anomaly-stats-grid">
        <StatCard
          label="Total tracks"
          value={formatNumber(summary.total_tracks)}
          detail="Full inference dataset"
          icon={Database}
        />

        <StatCard
          label="Scored tracks"
          value={formatNumber(summary.scored_tracks)}
          detail="Supported cluster assignments"
          icon={CheckCircle2}
        />

        <StatCard
          label="Flagged tracks"
          value={formatNumber(summary.flagged_tracks)}
          detail={`${summary.flag_rate_pct}% of scored tracks`}
          icon={AlertTriangle}
          tone="danger"
        />

        <StatCard
          label="Unassigned tracks"
          value={formatNumber(summary.unassigned_tracks)}
          detail="Not scored by cluster models"
          icon={Activity}
          tone="warning"
        />
      </div>

      <div className="anomaly-primary-grid">
        <ClusterAnalysis clusters={clusters} />
        <DetectionMethodology />
        <MonthlyTrend monthly={monthly} />
      </div>

      <VehicleReview vehicles={vehicles} />

      <TrackExplorer />

      <div className="anomaly-disclaimer">
        <AlertTriangle size={17} />
        <p>
          Isolation Forest identifies unusual observations; it does
          not establish the cause of an anomaly. A flagged track is
          a review signal, not proof of a mechanical fault or driver
          issue. Raw scores and thresholds are cluster-specific.
        </p>
      </div>
    </div>
  );
}
