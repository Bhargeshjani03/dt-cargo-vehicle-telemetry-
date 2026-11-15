
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
    } catch {
      // Keep the default error message.
    }

    throw new Error(message);
  }

  return response.json();
}

export function getOperationalInsights({
  minVehicleTracks = 30,
  topN = 10,
} = {}) {
  const params = new URLSearchParams({
    min_vehicle_tracks: String(minVehicleTracks),
    top_n: String(topN),
  });

  return request(`/tracks/insights?${params.toString()}`);
}
