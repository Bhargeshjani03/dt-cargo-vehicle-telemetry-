import 'dotenv/config';
import { createReadStream } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'csv-parse';
import { connectDatabase } from '../db.js';
import { Track, TrackFeature, Anomaly, ClusterEpisode } from '../models/index.js';

const ROOT = fileURLToPath(new URL('../../', import.meta.url));
const SOURCES = [
  [Track, 'data/processed/engineered_tracks.csv', ['track_id','vehicle_id','tour_id','fleet_test_id','start_time','stop_time','distance_km','duration_minutes','avg_speed_kmh','max_speed_kmh','gross_vehicle_weight','total_mass_with_trailer','axle_class'], ['track_id']],
  [TrackFeature, 'src/anomaly_detection/reports/full/modeling_dataset.csv', ['track_id','quality_status_core','quality_status_extended','reason_codes','ineligible_reasons_core','ineligible_reasons_extended','telemetry_coverage_ratio','raw_speed_mean_kmh','raw_speed_std','low_speed_time_pct_03','stop_episode_count_03','duration_minutes','distance_km'], ['track_id']],
  [Anomaly, 'src/anomaly_detection/reports/full/validation_predictions_extended_six_feature.csv', ['track_id','vehicle_id','start_time','anomaly_score','is_anomaly','model_variant','reason_codes','quality_status_extended','raw_speed_mean_kmh','raw_speed_std','low_speed_time_pct_03','stop_episode_count_03','duration_minutes','distance_km'], ['track_id']],
  [ClusterEpisode, 'data/processed/tour_level_clustering/12h_kernelpca_k3_tour_clusters.csv', ['vehicle_id','tour_id','episode_no','start_time','end_time','cluster','total_distance_km','elapsed_span_hours','recorded_track_hours','track_count','distance_based_avg_speed_kmh_clean','telemetry_flagged','fleet_test_id'], ['vehicle_id','tour_id','episode_no']],
];

function value(raw) {
  if (raw === '' || raw === undefined) return null;
  if (raw === 'True') return true;
  if (raw === 'False') return false;
  const n = Number(raw);
  return Number.isFinite(n) ? n : raw;
}

async function importFile(Model, relativePath, columns, keys) {
  const path = resolve(ROOT, relativePath);
  const parser = createReadStream(path).pipe(parse({ columns: true, skip_empty_lines: true, bom: true, relax_column_count: true }));
  let batch = [];
  let rows = 0;
  for await (const row of parser) {
    const document = Object.fromEntries(columns.map((column) => [column, value(row[column])]));
    const filter = Object.fromEntries(keys.map((key) => [key, document[key]]));
    batch.push({ updateOne: { filter, update: { $set: document }, upsert: true } });
    rows += 1;
    if (batch.length >= 500) {
      await Model.bulkWrite(batch, { ordered: false });
      batch = [];
    }
  }
  if (batch.length) await Model.bulkWrite(batch, { ordered: false });
  return rows;
}

await connectDatabase();
for (const [model, path, columns, keys] of SOURCES) {
  const count = await importFile(model, path, columns, keys);
  console.log(`${model.collection.collectionName}: upserted ${count} source rows`);
}
process.exit(0);
