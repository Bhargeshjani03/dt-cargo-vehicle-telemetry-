import { createReadStream, existsSync, readFileSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse';
import { parse as parseSync } from 'csv-parse/sync';
import { databaseReady } from '../db.js';
import { Track, TrackFeature, Anomaly, ClusterEpisode } from '../models/index.js';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const DATA = {
  tracks: resolve(ROOT, 'data/processed/engineered_tracks.csv'),
  features: resolve(ROOT, 'src/anomaly_detection/reports/full/modeling_dataset.csv'),
  anomalies: resolve(ROOT, 'src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv'),
  episodes: resolve(ROOT, 'data/processed/tour_level_clustering/12h_kernelpca_k3_tour_clusters.csv'),
  anomalySummary: resolve(ROOT, 'src/anomaly_detection/reports/full/validation_summary.json'),
  eligibility: resolve(ROOT, 'src/anomaly_detection/reports/eligibility_summary.json'),
  regressionMeta: resolve(ROOT, 'src/tour_duration/artifacts/tour_duration_v1.json'),
  speedRoot: resolve(ROOT, 'data/raw/speed'),
};

let indexPromise;

function number(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function boolean(value) {
  return ['true', '1', 'yes'].includes(String(value ?? '').trim().toLowerCase());
}

function dateMs(value) {
  if (value instanceof Date) return value.getTime();
  if (!value) return null;
  const normalized = String(value).includes(' ') ? String(value).replace(' ', 'T') : String(value);
  const parsed = Date.parse(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function splitReasons(value) {
  return String(value ?? '').split(';').map((item) => item.trim()).filter(Boolean);
}

async function* csvRows(path) {
  if (!existsSync(path)) return;
  const parser = createReadStream(path).pipe(parse({
    columns: true,
    skip_empty_lines: true,
    bom: true,
    relax_column_count: true,
  }));
  for await (const row of parser) yield row;
}

async function readCsvData() {
  const features = new Map();
  for await (const row of csvRows(DATA.features)) {
    const id = number(row.track_id);
    if (id === null) continue;
    features.set(id, {
      coreStatus: row.quality_status_core || row.quality_status || 'unknown',
      extendedStatus: row.quality_status_extended || row.quality_status || 'unknown',
      reasons: splitReasons(row.reason_codes),
      coreIneligibleReasons: splitReasons(row.ineligible_reasons_core),
      extendedIneligibleReasons: splitReasons(row.ineligible_reasons_extended),
      coverageRatio: number(row.telemetry_coverage_ratio),
      rawSpeedMeanKmh: number(row.raw_speed_mean_kmh),
      rawSpeedStd: number(row.raw_speed_std),
      lowSpeedPct03: number(row.low_speed_time_pct_03),
      stopEpisodeCount03: number(row.stop_episode_count_03),
      durationMinutes: number(row.duration_minutes),
      distanceKm: number(row.distance_km),
    });
  }

  const anomalies = new Map();
  for await (const row of csvRows(DATA.anomalies)) {
    const id = number(row.track_id);
    if (id === null) continue;
    anomalies.set(id, {
      score: number(row.anomaly_score),
      flagged: boolean(row.is_anomaly),
      modelVariant: row.model_variant || 'extended_six_feature',
      startMs: dateMs(row.start_time),
    });
  }

  const episodes = [];
  for await (const row of csvRows(DATA.episodes)) {
    const cluster = number(row.cluster);
    if (cluster === null) continue;
    episodes.push({
      vehicleId: number(row.vehicle_id),
      tourId: number(row.tour_id),
      episodeNo: number(row.episode_no),
      startMs: dateMs(row.start_time),
      endMs: dateMs(row.end_time),
      cluster,
      distanceKm: number(row.total_distance_km),
      elapsedHours: number(row.elapsed_span_hours),
      recordedHours: number(row.recorded_track_hours),
      trackCount: number(row.track_count),
      speedKmh: number(row.distance_based_avg_speed_kmh_clean),
      telemetryFlagged: boolean(row.telemetry_flagged),
      fleetTestId: number(row.fleet_test_id),
      matchedTrackCount: 0,
      stopsFromTracks: 0,
      episodeKey: `${row.vehicle_id}|${row.tour_id}|${row.episode_no}`,
    });
  }

  const byPair = new Map();
  for (const episode of episodes) {
    const key = `${episode.vehicleId}|${episode.tourId}`;
    if (!byPair.has(key)) byPair.set(key, []);
    byPair.get(key).push(episode);
  }
  for (const list of byPair.values()) list.sort((a, b) => (a.startMs ?? 0) - (b.startMs ?? 0));

  const tracks = [];
  for await (const row of csvRows(DATA.tracks)) {
    const id = number(row.track_id);
    const vehicleId = number(row.vehicle_id);
    if (id === null || vehicleId === null) continue;
    const startMs = dateMs(row.start_time);
    const pair = byPair.get(`${vehicleId}|${number(row.tour_id)}`) || [];
    const match = pair.find((episode) => episode.startMs !== null && episode.endMs !== null && startMs !== null && episode.startMs <= startMs && episode.endMs >= startMs) || null;
    const feature = features.get(id) || null;
    const anomaly = anomalies.get(id) || null;
    if (match) match.matchedTrackCount += 1;
    if (match && Number.isFinite(feature?.stopEpisodeCount03)) match.stopsFromTracks += feature.stopEpisodeCount03;
    tracks.push({
      trackId: id,
      vehicleId,
      tourId: number(row.tour_id),
      fleetTestId: number(row.fleet_test_id),
      startMs,
      stopMs: dateMs(row.stop_time),
      distanceKm: number(row.distance_km),
      durationMinutes: feature?.durationMinutes ?? number(row.duration_minutes),
      avgSpeedKmh: number(row.avg_speed_kmh),
      maxSpeedKmh: number(row.max_speed_kmh),
      grossVehicleWeight: number(row.gross_vehicle_weight),
      totalMassWithTrailer: number(row.total_mass_with_trailer),
      axleClass: number(row.axle_class),
      clusterId: match?.cluster ?? null,
      episodeKey: match?.episodeKey ?? null,
      quality: feature,
      anomaly,
    });
  }

  return { tracks, episodes, source: 'CSV snapshot' };
}

async function readMongoData() {
  if (!databaseReady()) return null;
  const [trackCount, episodeCount] = await Promise.all([
    Track.estimatedDocumentCount(),
    ClusterEpisode.estimatedDocumentCount(),
  ]);
  if (!trackCount || !episodeCount) return null;
  const [trackDocs, featureDocs, anomalyDocs, episodeDocs] = await Promise.all([
    Track.find().lean().exec(), TrackFeature.find().lean().exec(),
    Anomaly.find().lean().exec(), ClusterEpisode.find().lean().exec(),
  ]);
  const features = new Map(featureDocs.map((row) => [number(row.track_id), {
    coreStatus: row.quality_status_core || 'unknown',
    extendedStatus: row.quality_status_extended || 'unknown',
    reasons: splitReasons(row.reason_codes),
    coreIneligibleReasons: splitReasons(row.ineligible_reasons_core),
    extendedIneligibleReasons: splitReasons(row.ineligible_reasons_extended),
    coverageRatio: number(row.telemetry_coverage_ratio),
    rawSpeedMeanKmh: number(row.raw_speed_mean_kmh),
    rawSpeedStd: number(row.raw_speed_std),
    lowSpeedPct03: number(row.low_speed_time_pct_03),
    stopEpisodeCount03: number(row.stop_episode_count_03),
    durationMinutes: number(row.duration_minutes),
    distanceKm: number(row.distance_km),
  }]));
  const anomalies = new Map(anomalyDocs.map((row) => [number(row.track_id), {
    score: number(row.anomaly_score), flagged: boolean(row.is_anomaly),
    modelVariant: row.model_variant || 'extended_six_feature', startMs: dateMs(row.start_time),
  }]));
  const episodes = episodeDocs.map((row) => ({
    vehicleId: number(row.vehicle_id), tourId: number(row.tour_id), episodeNo: number(row.episode_no),
    startMs: dateMs(row.start_time), endMs: dateMs(row.end_time), cluster: number(row.cluster),
    distanceKm: number(row.total_distance_km), elapsedHours: number(row.elapsed_span_hours),
    recordedHours: number(row.recorded_track_hours), trackCount: number(row.track_count),
    speedKmh: number(row.distance_based_avg_speed_kmh_clean), telemetryFlagged: boolean(row.telemetry_flagged),
    fleetTestId: number(row.fleet_test_id), matchedTrackCount: 0, stopsFromTracks: 0,
    episodeKey: `${row.vehicle_id}|${row.tour_id}|${row.episode_no}`,
  }));
  const byPair = new Map();
  for (const episode of episodes) {
    const key = `${episode.vehicleId}|${episode.tourId}`;
    if (!byPair.has(key)) byPair.set(key, []);
    byPair.get(key).push(episode);
  }
  for (const list of byPair.values()) list.sort((a, b) => (a.startMs ?? 0) - (b.startMs ?? 0));
  const tracks = trackDocs.map((row) => {
    const vehicleId = number(row.vehicle_id);
    const startMs = dateMs(row.start_time);
    const pair = byPair.get(`${vehicleId}|${number(row.tour_id)}`) || [];
    const match = pair.find((episode) => episode.startMs !== null && episode.endMs !== null && startMs !== null && episode.startMs <= startMs && episode.endMs >= startMs) || null;
    const feature = features.get(number(row.track_id)) || null;
    if (match) match.matchedTrackCount += 1;
    if (match && Number.isFinite(feature?.stopEpisodeCount03)) match.stopsFromTracks += feature.stopEpisodeCount03;
    return {
      trackId: number(row.track_id), vehicleId, tourId: number(row.tour_id), fleetTestId: number(row.fleet_test_id),
      startMs, stopMs: dateMs(row.stop_time), distanceKm: number(row.distance_km),
      durationMinutes: feature?.durationMinutes ?? number(row.duration_minutes),
      avgSpeedKmh: number(row.avg_speed_kmh), maxSpeedKmh: number(row.max_speed_kmh),
      grossVehicleWeight: number(row.gross_vehicle_weight), totalMassWithTrailer: number(row.total_mass_with_trailer),
      axleClass: number(row.axle_class), clusterId: match?.cluster ?? null, episodeKey: match?.episodeKey ?? null,
      quality: feature, anomaly: anomalies.get(number(row.track_id)) || null,
    };
  });
  return { tracks, episodes, source: 'MongoDB' };
}

async function buildIndex() {
  const mongoData = await readMongoData().catch(() => null);
  const raw = mongoData || await readCsvData();
  const tracksById = new Map(raw.tracks.map((track) => [track.trackId, track]));
  const anomalies = raw.tracks.filter((track) => track.anomaly).map((track) => ({
    trackId: track.trackId, vehicleId: track.vehicleId, startMs: track.startMs,
    clusterId: track.clusterId, score: track.anomaly.score, flagged: track.anomaly.flagged,
    modelVariant: track.anomaly.modelVariant, quality: track.quality,
  }));
  const clusterById = new Map([0, 1, 2].map((id) => [id, raw.episodes.filter((episode) => episode.cluster === id)]));
  const clusterProfiles = [0, 1, 2].map((id) => {
    const rows = clusterById.get(id) || [];
    const vehicles = new Set(rows.map((row) => row.vehicleId));
    return {
      cluster: id,
      episodes: rows.length,
      vehicles: vehicles.size,
      medianDistanceKm: median(rows.map((row) => row.distanceKm)),
      medianElapsedHours: median(rows.map((row) => row.elapsedHours)),
      medianRecordedHours: median(rows.map((row) => row.recordedHours)),
      medianTracksPerEpisode: median(rows.map((row) => row.trackCount)),
      medianSpeedKmh: median(rows.map((row) => row.speedKmh)),
      medianTrackStopEpisodes: median(rows.filter((row) => row.matchedTrackCount > 0).map((row) => row.stopsFromTracks)),
      monthly: groupByMonth(rows),
    };
  });
  const typicalByCluster = new Map([0, 1, 2].map((cluster) => {
    const rows = raw.tracks.filter((track) => track.clusterId === cluster);
    return [cluster, {
      tracks: rows.length,
      medianDistanceKm: median(rows.map((row) => row.distanceKm)),
      medianDurationMinutes: median(rows.map((row) => row.durationMinutes)),
      medianSpeedKmh: median(rows.map((row) => row.avgSpeedKmh)),
      medianStops: median(rows.map((row) => row.quality?.stopEpisodeCount03)),
    }];
  }));
  return { ...raw, tracksById, anomalies, clusterProfiles, typicalByCluster };
}

function median(values) {
  const valid = values.filter((value) => value !== null && value !== undefined && Number.isFinite(Number(value))).map(Number).sort((a, b) => a - b);
  if (!valid.length) return null;
  const middle = Math.floor(valid.length / 2);
  return valid.length % 2 ? valid[middle] : (valid[middle - 1] + valid[middle]) / 2;
}

function monthKey(ms) {
  return ms === null ? null : new Date(ms).toISOString().slice(0, 7);
}

function groupByMonth(rows) {
  const map = new Map();
  for (const row of rows) {
    const month = monthKey(row.startMs);
    if (month) map.set(month, (map.get(month) || 0) + 1);
  }
  return [...map.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([month, episodes]) => ({ month, episodes }));
}

export function getIndex() {
  if (!indexPromise) indexPromise = buildIndex();
  return indexPromise;
}

function inRange(ms, from, to) {
  if (!from && !to) return true;
  if (ms === null) return false;
  const start = from ? Date.parse(`${from}T00:00:00Z`) : -Infinity;
  const end = to ? Date.parse(`${to}T23:59:59.999Z`) : Infinity;
  return ms >= start && ms <= end;
}

function filterTracks(index, query = {}) {
  const cluster = query.cluster === undefined || query.cluster === '' ? null : query.cluster === 'unassigned' ? 'unassigned' : number(query.cluster);
  return index.tracks.filter((row) => {
    if (!inRange(row.startMs, query.from, query.to)) return false;
    if (query.fleetTestId && String(row.fleetTestId) !== String(query.fleetTestId)) return false;
    if (cluster === 'unassigned' && row.clusterId !== null) return false;
    if (cluster !== null && cluster !== 'unassigned' && row.clusterId !== cluster) return false;
    if (query.vehicleId && String(row.vehicleId) !== String(query.vehicleId)) return false;
    if (query.qualityStatus && row.quality?.extendedStatus !== query.qualityStatus) return false;
    if (query.anomalyStatus === 'flagged' && !row.anomaly?.flagged) return false;
    if (query.anomalyStatus === 'unflagged' && row.anomaly?.flagged) return false;
    return true;
  });
}

function activityByMonth(rows) {
  const months = new Map();
  for (const row of rows) {
    const key = monthKey(row.startMs);
    if (!key) continue;
    if (!months.has(key)) months.set(key, { month: key, tracks: 0, vehicles: new Set(), distanceKm: 0, flagged: 0 });
    const item = months.get(key);
    item.tracks += 1;
    item.vehicles.add(row.vehicleId);
    item.distanceKm += Math.max(0, row.distanceKm || 0);
    if (row.anomaly?.flagged) item.flagged += 1;
  }
  return [...months.values()].sort((a, b) => a.month.localeCompare(b.month)).map((row) => ({
    month: row.month, tracks: row.tracks, activeVehicles: row.vehicles.size,
    distanceKm: Math.round(row.distanceKm * 10) / 10, flagged: row.flagged,
  }));
}

function pageRows(rows, query = {}) {
  const page = Math.max(1, number(query.page) || 1);
  const pageSize = Math.min(100, Math.max(1, number(query.pageSize) || 25));
  const start = (page - 1) * pageSize;
  return { items: rows.slice(start, start + pageSize), page, pageSize, total: rows.length };
}

export async function getFilterOptions() {
  const index = await getIndex();
  const profilesByVehicle = new Map();
  const fleetGroups = new Set();
  const weights = new Set();
  const masses = new Set();
  const axles = new Set();
  let firstDate = Infinity;
  let lastDate = -Infinity;
  for (const row of index.tracks) {
    if (!profilesByVehicle.has(row.vehicleId)) profilesByVehicle.set(row.vehicleId, { vehicleId: row.vehicleId, weight: row.grossVehicleWeight, mass: row.totalMassWithTrailer, axle: row.axleClass });
    if (row.fleetTestId !== null) fleetGroups.add(row.fleetTestId);
    if (row.grossVehicleWeight !== null) weights.add(row.grossVehicleWeight);
    if (row.totalMassWithTrailer !== null) masses.add(row.totalMassWithTrailer);
    if (row.axleClass !== null) axles.add(row.axleClass);
    if (row.startMs !== null) {
      firstDate = Math.min(firstDate, row.startMs);
      lastDate = Math.max(lastDate, row.startMs);
    }
  }
  return {
    firstDate: Number.isFinite(firstDate) ? new Date(firstDate).toISOString().slice(0, 10) : null,
    lastDate: Number.isFinite(lastDate) ? new Date(lastDate).toISOString().slice(0, 10) : null,
    fleetGroups: [...fleetGroups].sort((a, b) => a - b),
    vehicles: [...profilesByVehicle.values()].sort((a, b) => a.vehicleId - b.vehicleId),
    weights: [...weights].sort((a, b) => a - b), masses: [...masses].sort((a, b) => a - b), axles: [...axles].sort((a, b) => a - b),
    clusters: [0, 1, 2], source: index.source,
  };
}

export async function getOverview(query = {}) {
  const index = await getIndex();
  const tracks = filterTracks(index, query);
  const vehicles = new Set(tracks.map((row) => row.vehicleId));
  const fleets = new Set(tracks.map((row) => row.fleetTestId).filter((value) => value !== null));
  const distanceKm = tracks.reduce((sum, row) => sum + Math.max(0, row.distanceKm || 0), 0);
  const assigned = tracks.filter((row) => row.clusterId !== null).length;
  const selectedEpisodeKeys = new Set(tracks.map((row) => row.episodeKey).filter(Boolean));
  const episodes = index.episodes.filter((row) => selectedEpisodeKeys.has(row.episodeKey));
  const clusterCounts = [0, 1, 2].map((cluster) => ({ cluster, episodes: episodes.filter((row) => row.cluster === cluster).length }));
  const validation = tracks.filter((row) => row.anomaly);
  const flagged = validation.filter((row) => row.anomaly?.flagged);
  const monthly = activityByMonth(tracks);
  const frequent = new Map();
  for (const row of flagged) frequent.set(row.vehicleId, (frequent.get(row.vehicleId) || 0) + 1);
  const topVehicle = [...frequent.entries()].sort((a, b) => b[1] - a[1])[0];
  const largestCluster = [...clusterCounts].sort((a, b) => b.episodes - a.episodes)[0];
  const vehicleActivity = new Map();
  for (const row of tracks) {
    if (!vehicleActivity.has(row.vehicleId)) vehicleActivity.set(row.vehicleId, { vehicleId: row.vehicleId, tracks: 0, distanceKm: 0, durationMinutes: 0 });
    const item = vehicleActivity.get(row.vehicleId);
    item.tracks += 1;
    item.distanceKm += Math.max(0, row.distanceKm || 0);
    item.durationMinutes += Math.max(0, row.durationMinutes || 0);
  }
  const mostActiveVehicles = [...vehicleActivity.values()]
    .sort((a, b) => b.durationMinutes - a.durationMinutes)
    .slice(0, 6)
    .map((row) => ({ ...row, distanceKm: Math.round(row.distanceKm * 10) / 10, durationHours: Math.round(row.durationMinutes / 60 * 10) / 10 }));
  return {
    source: index.source,
    metrics: { vehicles: vehicles.size, fleetTestGroups: fleets.size, tracks: tracks.length, distanceKm: Math.round(distanceKm * 10) / 10, assignedTracks: assigned, unassignedTracks: tracks.length - assigned },
    anomalies: { flagged: flagged.length, validationTracks: validation.length, policyRate: validation.length ? flagged.length / validation.length : null, scope: 'Saved validation-period scores only; review candidates, not prevalence.' },
    clusterCounts,
    monthly,
    mostActiveVehicles,
    insights: [
      largestCluster?.episodes ? `Cluster ${largestCluster.cluster} has the most saved 12-hour episodes in this window (${largestCluster.episodes.toLocaleString()}).` : 'No saved cluster episodes match this window.',
      topVehicle ? `Vehicle ${topVehicle[0]} has the most flagged validation tracks in this window (${topVehicle[1]}).` : 'No flagged validation tracks match this window.',
      monthly.length ? `${monthly[monthly.length - 1].month} recorded ${monthly[monthly.length - 1].tracks.toLocaleString()} tracks.` : 'No dated track activity is available in this window.',
    ],
    clusters: index.clusterProfiles,
    coverageNote: 'The saved episode assignments map uniquely to 151,398 tracks; unmatched tracks remain unassigned.',
  };
}

export async function getClusters() {
  const index = await getIndex();
  return { source: index.source, profiles: index.clusterProfiles, assignedEpisodes: index.episodes.length, monthly: [0, 1, 2].flatMap((cluster) => index.clusterProfiles[cluster].monthly.map((row) => ({ ...row, cluster }))) };
}

export async function getAnomalies(query = {}) {
  const index = await getIndex();
  const q = String(query.search || '').trim();
  let rows = index.anomalies.filter((row) => {
    if (query.status === 'flagged' && !row.flagged) return false;
    if (query.status === 'unflagged' && row.flagged) return false;
    if (query.vehicleId && String(row.vehicleId) !== String(query.vehicleId)) return false;
    if (query.cluster !== undefined && query.cluster !== '') {
      if (query.cluster === 'unassigned' ? row.clusterId !== null : row.clusterId !== number(query.cluster)) return false;
    }
    if (!inRange(row.startMs, query.from, query.to)) return false;
    if (q && !String(row.trackId).includes(q) && !String(row.vehicleId).includes(q)) return false;
    return true;
  }).sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity));
  const flaggedTotal = rows.filter((row) => row.flagged).length;
  const validationTotal = index.anomalies.filter((row) => inRange(row.startMs, query.from, query.to)).length;
  const frequency = new Map();
  for (const row of index.anomalies) if (row.flagged) frequency.set(row.vehicleId, (frequency.get(row.vehicleId) || 0) + 1);
  const frequentVehicles = [...frequency.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([vehicleId, count]) => ({ vehicleId, flaggedTracks: count }));
  const result = pageRows(rows, query);
  return {
    ...result,
    items: result.items.map((row) => ({ ...row, startTime: row.startMs ? new Date(row.startMs).toISOString() : null, qualityStatus: index.tracksById.get(row.trackId)?.quality?.extendedStatus || 'unknown', reasons: index.tracksById.get(row.trackId)?.quality?.reasons || [] })),
    flaggedTotal, validationTracks: validationTotal, frequentVehicles,
    threshold: 0.16479195421062676,
    thresholdMeaning: 'Negative Isolation Forest decision_function; higher scores are more unusual, not probabilities.',
    attributionNote: 'The model does not publish per-feature attribution. The detail view shows observed feature values and quality flags separately.',
  };
}

export async function getVehicles(query = {}) {
  const index = await getIndex();
  const grouped = new Map();
  for (const row of filterTracks(index, query)) {
    if (!grouped.has(row.vehicleId)) grouped.set(row.vehicleId, { vehicleId: row.vehicleId, tracks: 0, distanceKm: 0, durationMinutes: 0, flaggedTracks: 0, clusters: new Set(), specs: { weight: row.grossVehicleWeight, mass: row.totalMassWithTrailer, axle: row.axleClass } });
    const item = grouped.get(row.vehicleId);
    item.tracks += 1;
    item.distanceKm += Math.max(0, row.distanceKm || 0);
    item.durationMinutes += Math.max(0, row.durationMinutes || 0);
    if (row.anomaly?.flagged) item.flaggedTracks += 1;
    if (row.clusterId !== null) item.clusters.add(row.clusterId);
  }
  let items = [...grouped.values()].map((row) => ({ ...row, clusters: [...row.clusters], distanceKm: Math.round(row.distanceKm * 10) / 10, durationHours: Math.round(row.durationMinutes / 60 * 10) / 10 }));
  const q = String(query.search || '').trim();
  if (q) items = items.filter((row) => String(row.vehicleId).includes(q));
  items.sort((a, b) => b.tracks - a.tracks);
  return pageRows(items, query);
}

export async function getVehicle(vehicleId) {
  const index = await getIndex();
  const id = number(vehicleId);
  const rows = index.tracks.filter((row) => row.vehicleId === id).sort((a, b) => (b.startMs || 0) - (a.startMs || 0));
  if (!rows.length) return null;
  const clusters = new Map();
  const monthly = new Map();
  const episodeKeys = new Set();
  for (const row of rows) {
    const month = monthKey(row.startMs);
    if (month) monthly.set(month, (monthly.get(month) || 0) + 1);
    if (row.clusterId !== null) {
      const key = `${row.clusterId}|${row.episodeKey}`;
      if (!episodeKeys.has(key)) {
        clusters.set(row.clusterId, (clusters.get(row.clusterId) || 0) + 1);
        episodeKeys.add(key);
      }
    }
  }
  const flagged = rows.filter((row) => row.anomaly?.flagged);
  const profile = rows[0];
  return {
    vehicle: { vehicleId: id, grossVehicleWeight: profile.grossVehicleWeight, totalMassWithTrailer: profile.totalMassWithTrailer, axleClass: profile.axleClass },
    metrics: { tracks: rows.length, tours: new Set(rows.map((row) => row.tourId)).size, distanceKm: Math.round(rows.reduce((sum, row) => sum + Math.max(0, row.distanceKm || 0), 0) * 10) / 10, durationHours: Math.round(rows.reduce((sum, row) => sum + Math.max(0, row.durationMinutes || 0), 0) / 60 * 10) / 10, flaggedTracks: flagged.length, validationTracks: rows.filter((row) => row.anomaly).length },
    clusters: [...clusters.entries()].sort((a, b) => a[0] - b[0]).map(([cluster, episodes]) => ({ cluster, episodes })),
    monthly: [...monthly.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([month, tracks]) => ({ month, tracks })),
    recentTracks: rows.slice(0, 25).map(trackSummary),
    frequentAnomalies: flagged.slice(0, 10).map(trackSummary),
  };
}

function trackSummary(row) {
  return {
    trackId: row.trackId, vehicleId: row.vehicleId, tourId: row.tourId,
    startTime: row.startMs ? new Date(row.startMs).toISOString() : null,
    distanceKm: row.distanceKm, durationMinutes: row.durationMinutes, avgSpeedKmh: row.avgSpeedKmh,
    clusterId: row.clusterId, qualityStatus: row.quality?.extendedStatus || 'unknown',
    anomalyScore: row.anomaly?.score ?? null, isAnomaly: row.anomaly?.flagged ?? null,
  };
}

export async function getTracks(query = {}) {
  const index = await getIndex();
  const q = String(query.search || '').trim();
  let rows = filterTracks(index, query);
  if (q) rows = rows.filter((row) => String(row.trackId).includes(q) || String(row.vehicleId).includes(q));
  rows.sort((a, b) => (b.startMs || 0) - (a.startMs || 0));
  const result = pageRows(rows, query);
  return { ...result, items: result.items.map(trackSummary) };
}

export async function getTrack(trackId) {
  const index = await getIndex();
  const row = index.tracksById.get(number(trackId));
  if (!row) return null;
  const feature = row.quality || {};
  const anomaly = row.anomaly;
  return {
    track: {
      ...trackSummary(row), stopTime: row.stopMs ? new Date(row.stopMs).toISOString() : null,
      fleetTestId: row.fleetTestId, grossVehicleWeight: row.grossVehicleWeight,
      totalMassWithTrailer: row.totalMassWithTrailer, axleClass: row.axleClass,
    },
    quality: {
      coreStatus: feature.coreStatus || 'unknown', extendedStatus: feature.extendedStatus || 'unknown',
      reasons: feature.reasons || [], coreIneligibleReasons: feature.coreIneligibleReasons || [],
      extendedIneligibleReasons: feature.extendedIneligibleReasons || [], coverageRatio: feature.coverageRatio,
    },
    features: {
      rawSpeedMeanKmh: feature.rawSpeedMeanKmh, rawSpeedStd: feature.rawSpeedStd,
      lowSpeedTimePct03: feature.lowSpeedPct03, stopEpisodeCount03: feature.stopEpisodeCount03,
      durationMinutes: feature.durationMinutes, distanceKm: feature.distanceKm,
    },
    anomaly: anomaly ? { score: anomaly.score, flagged: anomaly.flagged, modelVariant: anomaly.modelVariant, threshold: 0.16479195421062676 } : null,
    typicalCluster: row.clusterId === null ? null : index.typicalByCluster.get(row.clusterId),
  };
}

export async function getTrackTelemetry(trackId) {
  const index = await getIndex();
  const row = index.tracksById.get(number(trackId));
  if (!row) return null;
  const directory = resolve(DATA.speedRoot, String(row.vehicleId));
  const path = resolve(directory, `${row.trackId}.csv`);
  if (!path.startsWith(directory + sep) || !existsSync(path)) return null;
  const content = await readFile(path, 'utf8');
  const parsed = parseSync(content, { columns: true, skip_empty_lines: true, bom: true, relax_column_count: true });
  const stride = Math.max(1, Math.ceil(parsed.length / 800));
  const points = [];
  for (let i = 0; i < parsed.length; i += stride) {
    const epoch = number(parsed[i].epoch);
    const speed = number(parsed[i].speed);
    if (epoch === null || speed === null) continue;
    points.push({ time: epoch < 100000000000 ? epoch * 1000 : epoch, speedKmh: Math.max(0, speed * 3.6), hdop: number(parsed[i].hdop) });
  }
  return { trackId: row.trackId, totalPoints: parsed.length, points, unit: 'km/h', source: 'raw telemetry speed (m/s converted to km/h)' };
}

export async function getQualitySummary() {
  const index = await getIndex();
  const statusCounts = { eligible: 0, eligible_with_warnings: 0, ineligible: 0, unknown: 0 };
  const reasons = new Map();
  const missing = { rawSpeedMeanKmh: 0, rawSpeedStd: 0, lowSpeedTimePct03: 0, stopEpisodeCount03: 0, distanceKm: 0, durationMinutes: 0 };
  for (const row of index.tracks) {
    const status = row.quality?.extendedStatus || 'unknown';
    statusCounts[status] = (statusCounts[status] || 0) + 1;
    for (const reason of row.quality?.reasons || []) reasons.set(reason, (reasons.get(reason) || 0) + 1);
    for (const key of Object.keys(missing)) if (row.quality?.[key] === null || row.quality?.[key] === undefined) missing[key] += 1;
  }
  return { tracks: index.tracks.length, statusCounts, missingFeatures: missing, reasonCounts: [...reasons.entries()].sort((a, b) => b[1] - a[1]).map(([reason, count]) => ({ reason, count })), source: index.source };
}

export async function getQualityRecords(query = {}) {
  const index = await getIndex();
  const status = String(query.status || 'ineligible');
  const rows = index.tracks.filter((row) => status === 'all' || row.quality?.extendedStatus === status).sort((a, b) => (b.startMs || 0) - (a.startMs || 0));
  const result = pageRows(rows, query);
  return { ...result, items: result.items.map((row) => ({ ...trackSummary(row), reasons: row.quality?.reasons || [], extendedIneligibleReasons: row.quality?.extendedIneligibleReasons || [] })) };
}

export async function getMethodology() {
  let anomaly = null;
  let eligibility = null;
  let regression = null;
  try { anomaly = JSON.parse(readFileSync(DATA.anomalySummary, 'utf8')); } catch {}
  try { eligibility = JSON.parse(readFileSync(DATA.eligibility, 'utf8')); } catch {}
  try { regression = JSON.parse(readFileSync(DATA.regressionMeta, 'utf8')); } catch {}
  return {
    anomaly: {
      family: 'Isolation Forest',
      variant: 'extended_six_feature',
      features: ['raw_speed_mean_kmh', 'raw_speed_std', 'low_speed_time_pct_03', 'stop_episode_count_03', 'duration_minutes', 'distance_km'],
      threshold: 0.16479195421062676,
      scoreMeaning: 'Negative decision_function; higher values are more unusual, not probabilities.',
      reviewPolicy: 'Threshold is the validation 98th percentile, selected for a 2% review target.',
      validation: anomaly?.extended_six_feature || null,
      limitation: 'No verified anomaly labels are available. A flag is a review candidate, not a diagnosis or prevalence estimate.',
    },
    regression,
    eligibility,
    clusters: {
      assignmentFile: '12h_kernelpca_k3_tour_clusters.csv',
      grain: 'one row per saved (vehicle_id, tour_id, episode_no)',
      featureContext: ['total distance', 'speed summaries', 'elapsed span and recorded track time'],
      interpretation: 'Cluster IDs are descriptive groups, not operational classes. The dashboard consumes saved labels and does not refit them.',
      stopContext: 'Cluster stop counts are sums of track-level stop episodes mapped to each saved episode; they are not deduplicated stop locations.',
    },
    limits: [
      'No latitude/longitude is present in the supplied track files; the route simulator is illustrative, not GPS playback.',
      'Anomaly feature values and quality flags are shown as context; per-feature model attribution is not available.',
      'Tour-duration training uses historical realized distance as a proxy for the planned-distance input. Validate against planned-route outcomes before operational use.',
    ],
  };
}

export async function getPredictionMetadata() {
  try { return JSON.parse(await readFile(DATA.regressionMeta, 'utf8')); }
  catch { return { available: false, status: 'not_trained', message: 'The duration model artifact is not available. Run npm run model:train from the project root.' }; }
}
