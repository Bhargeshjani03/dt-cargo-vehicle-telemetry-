
import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getVehicleSummary,
  getVehicles,
  getVehicleDetail,
} from "../../services/api/vehicleApi";

import "./vehicleIntelligence.css";
import VehicleTrackHistory from "./VehicleTrackHistory";
const number = (value) =>
  Number(value || 0).toLocaleString("en-IN");

const decimal = (value, digits = 2) =>
  value == null ? "—" : Number(value).toFixed(digits);

const date = (value) => {
  if (!value) return "—";

  return new Date(value).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

const clusterColors = ["#2563eb", "#d97706", "#0d9488"];

function MetricCard({ label, value, detail, icon }) {
  return (
    <div className="vi-metric-card">
      <div className="vi-metric-heading">
        <span>{label}</span>
        <span className="vi-metric-icon">{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="vi-state">
      <div className="vi-spinner" />
      <p>Loading vehicle intelligence...</p>
    </div>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <div className="vi-error">
      <strong>Unable to load Vehicle Intelligence</strong>
      <p>{message}</p>
      <button onClick={onRetry}>Try again</button>
    </div>
  );
}

function VehicleDirectory({
  vehicles,
  selectedVehicle,
  onSelect,
  loading,
  page,
  totalPages,
  onPageChange,
  search,
  onSearchChange,
  minimumTracks,
  onMinimumTracksChange,
  anomalyOnly,
  onAnomalyOnlyChange,
}) {
  return (
    <section className="vi-panel">
      <div className="vi-panel-heading">
        <div>
          <span className="vi-eyebrow">FLEET EXPLORER</span>
          <h2>Vehicle directory</h2>
          <p>Search and investigate individual fleet vehicles.</p>
        </div>
        <span className="vi-count">{vehicles.length} displayed</span>
      </div>

      <div className="vi-filters">
        <input
          type="search"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Search vehicle ID or fleet specifications..."
          aria-label="Search vehicles"
        />

        <select
          value={minimumTracks}
          onChange={(event) =>
            onMinimumTracksChange(Number(event.target.value))
          }
          aria-label="Minimum track count"
        >
          <option value={0}>All track counts</option>
          <option value={30}>At least 30 tracks</option>
          <option value={100}>At least 100 tracks</option>
          <option value={500}>At least 500 tracks</option>
        </select>

        <label className="vi-checkbox">
          <input
            type="checkbox"
            checked={anomalyOnly}
            onChange={(event) =>
              onAnomalyOnlyChange(event.target.checked)
            }
          />
          Flagged tracks only
        </label>
      </div>

      <div className="vi-table-wrap">
        <table className="vi-table">
          <thead>
            <tr>
              <th>Vehicle</th>
              <th>Fleet test</th>
              <th>Tracks</th>
              <th>Flagged</th>
              <th>Flag rate</th>
              <th>Distance</th>
              <th>Specifications</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="vi-table-message">
                  Loading vehicles...
                </td>
              </tr>
            ) : vehicles.length === 0 ? (
              <tr>
                <td colSpan="7" className="vi-table-message">
                  No vehicles match your filters.
                </td>
              </tr>
            ) : (
              vehicles.map((vehicle) => (
                <tr
                  key={vehicle.vehicle_id}
                  className={
                    selectedVehicle === vehicle.vehicle_id
                      ? "vi-selected-row"
                      : ""
                  }
                  onClick={() => onSelect(vehicle.vehicle_id)}
                >
                  <td>
                    <button className="vi-vehicle-link">
                      Vehicle #{vehicle.vehicle_id}
                    </button>
                  </td>
                  <td>{vehicle.fleet_test_id ?? "—"}</td>
                  <td>{number(vehicle.track_count)}</td>
                  <td>{number(vehicle.flagged_tracks)}</td>
                  <td>
                    {vehicle.flag_rate_pct == null
                      ? "—"
                      : `${decimal(vehicle.flag_rate_pct)}%`}
                  </td>
                  <td>{number(vehicle.total_distance_km)} km</td>
                  <td>
                    {vehicle.gross_vehicle_weight == null
                      ? "Missing"
                      : `${number(vehicle.gross_vehicle_weight)} kg`}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="vi-pagination">
        <span>
          Page {page} of {Math.max(totalPages, 1)}
        </span>

        <div>
          <button
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
          >
            Previous
          </button>
          <button
            disabled={page >= totalPages || loading}
            onClick={() => onPageChange(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

function VehicleProfile({ detail, loading, error }) {
  if (loading) {
    return (
      <section className="vi-panel">
        <LoadingState />
      </section>
    );
  }

  if (error) {
    return (
      <section className="vi-panel">
        <div className="vi-error">
          <strong>Unable to load vehicle profile</strong>
          <p>{error}</p>
        </div>
      </section>
    );
  }

  if (!detail) {
    return (
      <section className="vi-panel vi-empty-profile">
        <div className="vi-empty-icon">▣</div>
        <h2>Select a vehicle</h2>
        <p>
          Choose a vehicle from the directory to inspect its activity,
          specifications and track-level anomaly history.
        </p>
      </section>
    );
  }

  const summary = detail.summary || {};
  const specs = detail.specifications || {};

  const clusters = (detail.cluster_distribution || []).map(
    (item, index) => ({
      ...item,
      name:
        item.name ||
        `Cluster ${item.cluster}`,
      color: clusterColors[index % clusterColors.length],
    })
  );

  const monthly = detail.monthly_history || [];

  return (
    <section className="vi-panel">
      <div className="vi-panel-heading">
        <div>
          <span className="vi-eyebrow">VEHICLE PROFILE</span>
          <h2>Vehicle #{detail.vehicle_id}</h2>
          <p>
            Observed {date(summary.first_observed)} –{" "}
            {date(summary.last_observed)}
          </p>
        </div>
        <span className="vi-profile-tag">TRACK AGGREGATION</span>
      </div>

      <div className="vi-spec-grid">
        <div>
          <span>Fleet test</span>
          <strong>{specs.fleet_test_id ?? "Unavailable"}</strong>
        </div>
        <div>
          <span>Gross vehicle weight</span>
          <strong>
            {specs.gross_vehicle_weight == null
              ? "Unavailable"
              : `${number(specs.gross_vehicle_weight)} kg`}
          </strong>
        </div>
        <div>
          <span>Total mass with trailer</span>
          <strong>
            {specs.total_mass_with_trailer == null
              ? "Unavailable"
              : `${number(specs.total_mass_with_trailer)} kg`}
          </strong>
        </div>
        <div>
          <span>Axle class</span>
          <strong>{specs.axle_class ?? "Unavailable"}</strong>
        </div>
      </div>

      <div className="vi-profile-metrics">
        <div>
          <span>Total tracks</span>
          <strong>{number(summary.track_count)}</strong>
        </div>
        <div>
          <span>Scored tracks</span>
          <strong>{number(summary.scored_tracks)}</strong>
        </div>
        <div>
          <span>Flagged tracks</span>
          <strong>{number(summary.flagged_tracks)}</strong>
        </div>
        <div>
          <span>Track flag rate</span>
          <strong>
            {summary.flag_rate_pct == null
              ? "—"
              : `${decimal(summary.flag_rate_pct)}%`}
          </strong>
        </div>
        <div>
          <span>Total distance</span>
          <strong>{number(summary.total_distance_km)} km</strong>
        </div>
        <div>
          <span>Median track duration</span>
          <strong>
            {decimal(summary.median_track_duration_minutes)} min
          </strong>
        </div>
      </div>

      <div className="vi-chart-grid">
        <div className="vi-chart-card">
          <div className="vi-chart-heading">
            <h3>Movement-cluster distribution</h3>
            <p>Track counts by assigned movement cluster</p>
          </div>

          {clusters.length === 0 ? (
            <div className="vi-chart-empty">
              No assigned movement clusters.
            </div>
          ) : (
            <>
              <div className="vi-chart">
                <ResponsiveContainer width="100%" height={260}>
                  <PieChart>
                    <Pie
                      data={clusters}
                      dataKey="track_count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={62}
                      outerRadius={95}
                      paddingAngle={3}
                    >
                      {clusters.map((item, index) => (
                        <Cell
                          key={item.cluster}
                          fill={clusterColors[index % clusterColors.length]}
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={(value) => [
                        number(value),
                        "Tracks",
                      ]}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="vi-cluster-list">
                {clusters.map((item) => (
                  <div key={item.cluster}>
                    <span
                      className="vi-cluster-dot"
                      style={{ background: item.color }}
                    />
                    <span>{item.name}</span>
                    <strong>{number(item.track_count)}</strong>
                    <small>{decimal(item.percentage)}%</small>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="vi-chart-card">
          <div className="vi-chart-heading">
            <h3>Monthly anomaly history</h3>
            <p>Track-level flags across observed months</p>
          </div>

          {monthly.length === 0 ? (
            <div className="vi-chart-empty">
              No monthly history available.
            </div>
          ) : (
            <div className="vi-chart">
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={monthly}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                    vertical={false}
                  />
                  <XAxis
                    dataKey="month"
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar
                    dataKey="scored_tracks"
                    name="Scored tracks"
                    fill="#94a3b8"
                    radius={[3, 3, 0, 0]}
                  />
                  <Bar
                    dataKey="flagged_tracks"
                    name="Flagged tracks"
                    fill="#dc7b42"
                    radius={[3, 3, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          <div className="vi-monthly-note">
            Flag rate is calculated from scored tracks only. A month with
            no scored tracks has no meaningful flag rate.
          </div>
        </div>
      </div>

      <div className="vi-interpretation">
        <strong>How to interpret this profile</strong>
        <p>{detail.interpretation}</p>
      </div>
      <VehicleTrackHistory vehicleId={detail.vehicle_id} />
    </section>
  );
}

export default function VehicleIntelligencePage() {
  const [summary, setSummary] = useState(null);
  const [vehicles, setVehicles] = useState([]);
  const [detail, setDetail] = useState(null);

  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [search, setSearch] = useState("");
  const [minimumTracks, setMinimumTracks] = useState(0);
  const [anomalyOnly, setAnomalyOnly] = useState(false);

  const [selectedVehicle, setSelectedVehicle] = useState(null);

  const [loading, setLoading] = useState(true);
  const [listLoading, setListLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const [error, setError] = useState("");
  const [detailError, setDetailError] = useState("");

  const loadSummary = useCallback(async () => {
    try {
      const result = await getVehicleSummary();
      setSummary(result);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadVehicles = useCallback(async () => {
    setListLoading(true);

    try {
      const result = await getVehicles({
        page,
        pageSize: 25,
        search,
        minimumTracks,
        anomalyOnly,
      });

      setVehicles(result.records || []);
      setTotalPages(result.total_pages || 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setListLoading(false);
    }
  }, [page, search, minimumTracks, anomalyOnly]);

  const loadDetail = useCallback(async (vehicleId) => {
    if (vehicleId == null) {
      setDetail(null);
      return;
    }

    setDetailLoading(true);
    setDetailError("");

    try {
      const result = await getVehicleDetail(vehicleId);
      setDetail(result);
    } catch (err) {
      setDetail(null);
      setDetailError(err.message);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  useEffect(() => {
    loadDetail(selectedVehicle);
  }, [selectedVehicle, loadDetail]);

  useEffect(() => {
    setPage(1);
  }, [search, minimumTracks, anomalyOnly]);

  if (loading && !summary) {
    return (
      <div className="vi-page">
        <LoadingState />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="vi-page">
        <ErrorState
          message={error}
          onRetry={loadSummary}
        />
      </div>
    );
  }

  return (
    <div className="vi-page">
      <header className="vi-hero">
        <div>
          <span className="vi-eyebrow">DT-CARGO / FLEET ANALYTICS</span>
          <h1>Vehicle Intelligence</h1>
          <p>
            Explore fleet composition, vehicle activity and unusual
            track-level movement patterns.
          </p>
        </div>

        <div className="vi-hero-meta">
          <span className="vi-live-dot" />
          Dataset loaded
          <small>163 registered vehicles</small>
        </div>
      </header>

      {error && (
        <div className="vi-inline-error">
          {error}
          <button onClick={loadVehicles}>Retry</button>
        </div>
      )}

      <section className="vi-metrics-grid">
        <MetricCard
          label="Total vehicles"
          value={number(summary?.total_vehicles)}
          detail={`${number(summary?.vehicles_with_scored_tracks)} with scored tracks`}
          icon="▣"
        />
        <MetricCard
          label="Total tracks"
          value={number(summary?.total_tracks)}
          detail={`${number(summary?.scored_tracks)} scored`}
          icon="↗"
        />
        <MetricCard
          label="Flagged tracks"
          value={number(summary?.flagged_tracks)}
          detail="Track-level anomaly flags"
          icon="!"
        />
        <MetricCard
          label="Overall flag rate"
          value={
            summary?.overall_flag_rate_pct == null
              ? "—"
              : `${decimal(summary.overall_flag_rate_pct)}%`
          }
          detail="Of scored tracks"
          icon="%"
        />
        <MetricCard
          label="Total distance"
          value={`${number(summary?.total_distance_km)}`}
          detail="Kilometres across all tracks"
          icon="⌁"
        />
        <MetricCard
          label="Missing specifications"
          value={number(summary?.vehicles_with_missing_specs)}
          detail="Vehicles without gross-weight data"
          icon="i"
        />
      </section>

      <div className="vi-dataset-note">
        <strong>Interpretation note</strong>
        <span>
          Vehicle statistics aggregate track-level predictions. A flagged
          track is a statistical outlier, not confirmation of a mechanical
          fault. Vehicles with fewer observations should be interpreted
          cautiously.
        </span>
      </div>

      <VehicleDirectory
        vehicles={vehicles}
        selectedVehicle={selectedVehicle}
        onSelect={setSelectedVehicle}
        loading={listLoading}
        page={page}
        totalPages={totalPages}
        onPageChange={setPage}
        search={search}
        onSearchChange={setSearch}
        minimumTracks={minimumTracks}
        onMinimumTracksChange={setMinimumTracks}
        anomalyOnly={anomalyOnly}
        onAnomalyOnlyChange={setAnomalyOnly}
      />

      <VehicleProfile
        detail={detail}
        loading={detailLoading}
        error={detailError}
      />
    </div>
  );
}
