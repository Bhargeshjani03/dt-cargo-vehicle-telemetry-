
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api";

async function request(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`);

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the HTTP status message.
    }

    throw new Error(message);
  }

  return response.json();
}

export const anomalyApi = {
  getSummary() {
    return request("/anomalies/summary");
  },

  getClusters() {
    return request("/anomalies/clusters");
  },

  getMonthly() {
    return request("/anomalies/monthly");
  },

  getVehicles(limit = 10, minTracks = 30) {
    const params = new URLSearchParams({
      limit: String(limit),
      min_tracks: String(minTracks),
    });

    return request(`/anomalies/vehicles?${params}`);
  },

  getQuality() {
    return request("/anomalies/quality");
  },

  getTracks(params = {}) {
    const query = new URLSearchParams();

    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        query.set(key, String(value));
      }
    });

    return request(`/anomalies/tracks?${query.toString()}`);
  },

  getTrack(trackId) {
    return request(
      `/anomalies/tracks/${encodeURIComponent(trackId)}`
    );
  },
};
