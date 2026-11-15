import express from 'express';
import * as handlers from './handlers.js';

const app = express();
app.disable('x-powered-by');
app.use(express.json({ limit: '12kb' }));
app.get('/api/health', handlers.health);
app.get('/api/filters', handlers.filters);
app.get('/api/overview', handlers.overview);
app.get('/api/clusters', handlers.clusters);
app.get('/api/anomalies', handlers.anomalies);
app.get('/api/vehicles', handlers.vehicles);
app.get('/api/vehicles/:vehicleId', handlers.vehicle);
app.get('/api/tracks', handlers.tracks);
app.get('/api/tracks/:trackId/telemetry', handlers.trackTelemetry);
app.get('/api/tracks/:trackId', handlers.track);
app.get('/api/quality', handlers.quality);
app.get('/api/quality/records', handlers.qualityRecords);
app.get('/api/methodology', handlers.methodology);
app.get('/api/prediction/model', handlers.predictionMetadata);
app.post('/api/prediction/duration', handlers.predictDuration);

export default app;
