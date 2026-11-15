
const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000/api";

async function request(endpoint) {
  const response = await fetch(`${API_BASE}${endpoint}`);

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;

    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {
      // Keep the original error message.
    }

    throw new Error(message);
  }

  return response.json();
}

export const getValidationSummary = () =>
  request("/regression/validation/summary");

export const getValidationPredictions = (page = 1, pageSize = 100) =>
  request(
    `/regression/validation/predictions?page=${page}&page_size=${pageSize}`
  );

export const getValidationClusters = () =>
  request("/regression/validation/clusters");

export const getErrorDistribution = () =>
  request("/regression/validation/error-distribution");

export const getDurationReliability = () =>
  request("/regression/validation/duration-reliability");

export const getRegressionModelInfo = () =>
  request("/regression/validation/model-info");
