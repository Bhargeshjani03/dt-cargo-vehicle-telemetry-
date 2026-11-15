
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api";

// --------------------------------------------------
// GENERIC API REQUEST
// --------------------------------------------------

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep default error message.
    }

    throw new Error(message);
  }

  return response.json();
}

// --------------------------------------------------
// TRACK DASHBOARD APIs
// --------------------------------------------------

export const getTrackSummary = () =>
  request("/tracks/summary");

export const getTrackTimeline = () =>
  request("/tracks/timeline");

export const getTrackDistributions = () =>
  request("/tracks/distributions");

export const getTrackClusters = () =>
  request("/tracks/clusters");

export const getTrackRelationships = () =>
  request("/tracks/relationships?sample_size=1500");

// --------------------------------------------------
// TRACK EXPLORER
// --------------------------------------------------

export function getTrackExplorer(params = {}) {
  const query = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (
      value !== undefined &&
      value !== null &&
      value !== ""
    ) {
      query.set(key, String(value));
    }
  });

  return request(
    `/tracks/explorer?${query.toString()}`
  );
}

// --------------------------------------------------
// INDIVIDUAL TRACK DETAILS
// --------------------------------------------------

export const getTrackDetail = (trackId) =>
  request(`/tracks/${encodeURIComponent(trackId)}`);

// --------------------------------------------------
// RAW SPEED PROFILE
// --------------------------------------------------

export const getTrackSpeedProfile = (trackId) =>
  request(
    `/tracks/${encodeURIComponent(trackId)}/speed-profile`
  );
