
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api";

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {}

    throw new Error(message);
  }

  return response.json();
}

export const getVehicleSummary = () =>
  request("/vehicles/summary");

export function getVehicles({
  page = 1,
  pageSize = 25,
  search = "",
  minimumTracks = 0,
  anomalyOnly = false,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    minimum_tracks: String(minimumTracks),
    anomaly_only: String(anomalyOnly),
  });

  if (search.trim()) {
    params.set("search", search.trim());
  }

  return request(`/vehicles?${params.toString()}`);
}

export const getVehicleDetail = (vehicleId) =>
  request(`/vehicles/${encodeURIComponent(vehicleId)}`);

export function getVehicleTracks(vehicleId, filters = {}) {
  const params = new URLSearchParams({
    page: String(filters.page ?? 1),
    page_size: String(filters.pageSize ?? 20),
    anomaly_status: filters.anomalyStatus ?? "all",
    sort_by: filters.sortBy ?? "newest",
  });

  if (filters.cluster !== "" && filters.cluster != null) {
    params.set("cluster", String(filters.cluster));
  }

  if (filters.dateFrom) {
    params.set("date_from", filters.dateFrom);
  }

  if (filters.dateTo) {
    params.set("date_to", filters.dateTo);
  }

  return request(
    `/vehicles/${encodeURIComponent(vehicleId)}/tracks?${params.toString()}`
  );
}
