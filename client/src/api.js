import { useEffect, useState } from 'react';

export async function requestJSON(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
  return data;
}

export function useApi(url) {
  const [state, setState] = useState({ data: null, error: '', loading: Boolean(url) });
  useEffect(() => {
    if (!url) return undefined;
    const controller = new AbortController();
    setState({ data: null, error: '', loading: true });
    requestJSON(url, { signal: controller.signal })
      .then((data) => setState({ data, error: '', loading: false }))
      .catch((error) => {
        if (error.name !== 'AbortError') setState({ data: null, error: error.message, loading: false });
      });
    return () => controller.abort();
  }, [url]);
  return state;
}

export function queryString(values) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) params.set(key, String(value));
  });
  return params.toString();
}
