import {
  getIndex, getFilterOptions, getOverview, getClusters, getAnomalies,
  getVehicles, getVehicle, getTracks, getTrack, getTrackTelemetry,
  getQualitySummary, getQualityRecords, getMethodology, getPredictionMetadata,
} from './services/telemetryStore.js';
import { runDurationPrediction } from './services/prediction.js';
import { databaseReady } from './db.js';

function fail(res, error, status = 500) {
  console.error('DT-CARGO API error:', error?.message || error);
  return res.status(status).json({ error: status === 500 ? 'Could not load this data view.' : error.message });
}

function queryOf(req) {
  return Object.fromEntries(['from', 'to', 'fleetTestId', 'vehicleId', 'cluster', 'status', 'qualityStatus', 'anomalyStatus', 'search', 'page', 'pageSize'].map((key) => [key, req.query[key]]));
}

export async function health(req, res) {
  return res.json({ ok: true, database: databaseReady() ? 'connected' : 'csv-fallback', app: 'dt-cargo' });
}

export async function filters(req, res) {
  try { return res.json(await getFilterOptions()); } catch (error) { return fail(res, error, 503); }
}

export async function overview(req, res) {
  try { return res.json(await getOverview(queryOf(req))); } catch (error) { return fail(res, error, 503); }
}

export async function clusters(req, res) {
  try { return res.json(await getClusters()); } catch (error) { return fail(res, error, 503); }
}

export async function anomalies(req, res) {
  try { return res.json(await getAnomalies(queryOf(req))); } catch (error) { return fail(res, error, 503); }
}

export async function vehicles(req, res) {
  try { return res.json(await getVehicles(queryOf(req))); } catch (error) { return fail(res, error, 503); }
}

export async function vehicle(req, res) {
  try {
    const result = await getVehicle(req.params.vehicleId);
    return result ? res.json(result) : res.status(404).json({ error: 'Vehicle was not found in the processed tracks.' });
  } catch (error) { return fail(res, error, 503); }
}

export async function tracks(req, res) {
  try { return res.json(await getTracks(queryOf(req))); } catch (error) { return fail(res, error, 503); }
}

export async function track(req, res) {
  try {
    const result = await getTrack(req.params.trackId);
    return result ? res.json(result) : res.status(404).json({ error: 'Track was not found in the processed tracks.' });
  } catch (error) { return fail(res, error, 503); }
}

export async function trackTelemetry(req, res) {
  try {
    const result = await getTrackTelemetry(req.params.trackId);
    return result ? res.json(result) : res.status(404).json({ error: 'Raw speed telemetry is not available for this track.' });
  } catch (error) { return fail(res, error, 503); }
}

export async function quality(req, res) {
  try { return res.json(await getQualitySummary()); } catch (error) { return fail(res, error, 503); }
}

export async function qualityRecords(req, res) {
  try { return res.json(await getQualityRecords(queryOf(req))); } catch (error) { return fail(res, error, 503); }
}

export async function methodology(req, res) {
  try { return res.json(await getMethodology()); } catch (error) { return fail(res, error, 503); }
}

export async function predictionMetadata(req, res) {
  try { return res.json(await getPredictionMetadata()); } catch (error) { return fail(res, error, 503); }
}

export async function predictDuration(req, res) {
  const input = req.body || {};
  const numeric = ['plannedDistanceKm', 'grossVehicleWeight', 'totalMassWithTrailer', 'axleClass', 'vehicleId'];
  for (const key of numeric) {
    if (!Number.isFinite(Number(input[key]))) return res.status(400).json({ error: `Enter a valid ${key}.` });
  }
  if (Number(input.plannedDistanceKm) <= 0 || Number(input.plannedDistanceKm) > 5000) return res.status(400).json({ error: 'Planned distance must be between 0 and 5,000 km.' });
  if (!Number.isFinite(Date.parse(input.departureAt))) return res.status(400).json({ error: 'Choose a valid planned departure date and time.' });
  try { return res.json(await runDurationPrediction(input)); }
  catch (error) { return fail(res, error, 503); }
}
