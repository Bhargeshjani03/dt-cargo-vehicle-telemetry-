
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getVehicleTracks } from "../../services/api/vehicleApi";

const formatNumber = (value, digits = 2) => {
  if (value == null || !Number.isFinite(Number(value))) {
    return "—";
  }

  return Number(value).toLocaleString("en-IN", {
    maximumFractionDigits: digits,
  });
};

const formatDate = (value) => {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function AnomalyStatus({ track }) {
  if (track.anomaly_score == null) {
    return <span className="vth-status vth-unscored">Unscored</span>;
  }

  if (track.is_anomaly) {
    return <span className="vth-status vth-flagged">Flagged</span>;
  }

  return <span className="vth-status vth-normal">Normal</span>;
}

export default function VehicleTrackHistory({ vehicleId }) {
  const navigate = useNavigate();

  const [result, setResult] = useState({
    records: [],
    total_records: 0,
    total_pages: 0,
  });

  const [page, setPage] = useState(1);
  const [cluster, setCluster] = useState("");
  const [anomalyStatus, setAnomalyStatus] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const [appliedFilters, setAppliedFilters] = useState({
    cluster: "",
    anomalyStatus: "all",
    sortBy: "newest",
    dateFrom: "",
    dateTo: "",
  });

  const [refreshKey, setRefreshKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadTracks = useCallback(async () => {
    if (vehicleId == null) return;

    setLoading(true);
    setError("");

    try {
      const data = await getVehicleTracks(vehicleId, {
        page,
        pageSize: 20,
        ...appliedFilters,
      });

      setResult(data);
    } catch (err) {
      setError(err.message);
      setResult({
        records: [],
        total_records: 0,
        total_pages: 0,
      });
    } finally {
      setLoading(false);
    }
  }, [vehicleId, page, appliedFilters, refreshKey]);

  useEffect(() => {
    loadTracks();
  }, [loadTracks]);

  useEffect(() => {
    setPage(1);
    setCluster("");
    setAnomalyStatus("all");
    setSortBy("newest");
    setDateFrom("");
    setDateTo("");

    setAppliedFilters({
      cluster: "",
      anomalyStatus: "all",
      sortBy: "newest",
      dateFrom: "",
      dateTo: "",
    });

    setRefreshKey((value) => value + 1);
  }, [vehicleId]);

  const applyFilters = () => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      setError("Start date cannot be later than end date.");
      return;
    }

    setPage(1);

    setAppliedFilters({
      cluster,
      anomalyStatus,
      sortBy,
      dateFrom,
      dateTo,
    });

    setRefreshKey((value) => value + 1);
  };

  const clearFilters = () => {
    setCluster("");
    setAnomalyStatus("all");
    setSortBy("newest");
    setDateFrom("");
    setDateTo("");

    setPage(1);

    setAppliedFilters({
      cluster: "",
      anomalyStatus: "all",
      sortBy: "newest",
      dateFrom: "",
      dateTo: "",
    });

    setRefreshKey((value) => value + 1);
  };

  const totalPages = Math.max(1, result.total_pages || 1);

  return (
    <section className="vth-section">
      <div className="vth-heading">
        <div>
          <span className="vi-eyebrow">TRACK-LEVEL INVESTIGATION</span>
          <h3>Vehicle track history</h3>
          <p>
            Inspect the individual tracks and anomaly predictions
            associated with this vehicle.
          </p>
        </div>

        <span className="vth-total">
          {Number(result.total_records || 0).toLocaleString("en-IN")} tracks
        </span>
      </div>

      <div className="vth-filters">
        <label>
          <span>From date</span>
          <input
            type="date"
            value={dateFrom}
            onChange={(event) => setDateFrom(event.target.value)}
          />
        </label>

        <label>
          <span>To date</span>
          <input
            type="date"
            value={dateTo}
            onChange={(event) => setDateTo(event.target.value)}
          />
        </label>

        <label>
          <span>Movement cluster</span>
          <select
            value={cluster}
            onChange={(event) => setCluster(event.target.value)}
          >
            <option value="">All clusters</option>
            <option value="0">0 · Active Transit</option>
            <option value="1">1 · Stop-Dominant</option>
            <option value="2">2 · Brief Near-Stationary</option>
          </select>
        </label>

        <label>
          <span>Anomaly status</span>
          <select
            value={anomalyStatus}
            onChange={(event) => setAnomalyStatus(event.target.value)}
          >
            <option value="all">All tracks</option>
            <option value="flagged">Flagged only</option>
            <option value="normal">Normal scored tracks</option>
            <option value="unscored">Unscored tracks</option>
          </select>
        </label>

        <label>
          <span>Sort by</span>
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="highest_score">Highest anomaly score</option>
          </select>
        </label>

        <div className="vth-filter-actions">
          <button onClick={applyFilters}>Apply filters</button>
          <button className="vth-clear" onClick={clearFilters}>
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div className="vth-error">
          {error}
          <button onClick={loadTracks}>Retry</button>
        </div>
      )}

      <div className="vth-table-meta">
        <span>
          {Number(result.total_records || 0).toLocaleString("en-IN")} matching
          tracks
        </span>
        <span>
          Page {page} of {totalPages}
        </span>
      </div>

      <div className="vth-table-wrap">
        <table className="vth-table">
          <thead>
            <tr>
              <th>Track</th>
              <th>Start time</th>
              <th>Distance</th>
              <th>Duration</th>
              <th>Movement cluster</th>
              <th>Anomaly score</th>
              <th>Status</th>
              <th>Quality</th>
              <th>Investigation</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan="9" className="vth-empty">
                  Loading vehicle tracks...
                </td>
              </tr>
            ) : result.records?.length ? (
              result.records.map((track) => (
                <tr key={track.track_id}>
                  <td>
                    <strong>#{track.track_id}</strong>
                  </td>

                  <td>{formatDate(track.start_time)}</td>

                  <td>{formatNumber(track.distance_km)} km</td>

                  <td>{formatNumber(track.duration_minutes)} min</td>

                  <td>
                    <span className="vth-cluster">
                      {track.cluster_name || "Unassigned"}
                    </span>
                  </td>

                  <td>
                    {formatNumber(track.anomaly_score, 5)}
                  </td>

                  <td>
                    <AnomalyStatus track={track} />
                  </td>

                  <td>
                    {(track.quality_status || "unscored").replaceAll(
                      "_",
                      " "
                    )}
                  </td>

                  <td>
                    <button
                      className="vth-investigate"
                      onClick={() =>
                        navigate(`/tracks?track_id=${track.track_id}`)
                      }
                    >
                      Inspect track →
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan="9" className="vth-empty">
                  No tracks match the selected filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="vth-pagination">
        <button
          disabled={page <= 1 || loading}
          onClick={() => setPage((value) => value - 1)}
        >
          Previous
        </button>

        <span>
          Page {page} / {totalPages}
        </span>

        <button
          disabled={page >= totalPages || loading}
          onClick={() => setPage((value) => value + 1)}
        >
          Next
        </button>
      </div>

      <p className="vth-footnote">
        Anomaly scores are track-level statistical scores. A flagged track
        is an unusual movement observation, not proof of a mechanical fault.
      </p>
    </section>
  );
}
