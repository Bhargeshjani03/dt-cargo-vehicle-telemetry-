import { useEffect, useMemo, useState } from 'react';
import { requestJSON, useApi } from '../api.js';
import { ErrorState, formatHours, LoadingState, MetricCard, PageHeader, Panel } from '../components/common.jsx';

function localDateTime(value) {
  const date = new Date(value);
  date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
  return date.toISOString().slice(0, 16);
}

export default function DurationPage() {
  const options = useApi('/api/filters');
  const metadata = useApi('/api/prediction/model');
  const [vehicleId, setVehicleId] = useState('');
  const [plannedDistanceKm, setDistance] = useState('150');
  const [weight, setWeight] = useState('');
  const [mass, setMass] = useState('');
  const [axle, setAxle] = useState('');
  const [departureAt, setDepartureAt] = useState(localDateTime(Date.now() + 86400000));
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const vehicles = options.data?.vehicles || [];
  const selectedProfile = useMemo(() => vehicles.find((item) => String(item.vehicleId) === String(vehicleId)), [vehicles, vehicleId]);

  useEffect(() => {
    if (!vehicles.length || vehicleId) return;
    const first = vehicles[0];
    setVehicleId(String(first.vehicleId));
    setWeight(String(first.weight ?? ''));
    setMass(String(first.mass ?? ''));
    setAxle(String(first.axle ?? ''));
  }, [vehicles, vehicleId]);

  useEffect(() => {
    if (!selectedProfile) return;
    setWeight(String(selectedProfile.weight ?? ''));
    setMass(String(selectedProfile.mass ?? ''));
    setAxle(String(selectedProfile.axle ?? ''));
  }, [selectedProfile]);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setResult(null);
    setSubmitting(true);
    try {
      const response = await requestJSON('/api/prediction/duration', {
        method: 'POST',
        body: JSON.stringify({
          vehicleId: Number(vehicleId),
          plannedDistanceKm: Number(plannedDistanceKm),
          grossVehicleWeight: Number(weight),
          totalMassWithTrailer: Number(mass),
          axleClass: Number(axle),
          departureAt: new Date(departureAt).toISOString(),
        }),
      });
      setResult(response);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSubmitting(false);
    }
  }

  const available = metadata.data?.available === true;
  const mainAction = { label: submitting ? 'Estimating…' : 'Estimate tour duration', onClick: () => document.getElementById('duration-form')?.requestSubmit(), disabled: !available || submitting };

  return (
    <div className="page-stack">
      <PageHeader eyebrow="PREDICTIVE ANALYSIS · REGRESSION" title="Tour Duration Prediction" description="Configure a hypothetical departure using vehicle specifications, planned distance, and departure timing." action={mainAction} />
      {options.loading || metadata.loading ? <LoadingState label="Loading vehicle profiles and model status…" /> : null}
      {metadata.error ? <ErrorState message={metadata.error} /> : null}
      {!available && metadata.data ? <div className="notice notice-red"><strong>Prediction model unavailable.</strong> {metadata.data.message || 'Train the model from the project root before submitting a scenario.'}</div> : null}
      <div className="dashboard-grid prediction-layout">
        <Panel title="Hypothetical tour" detail="Only fields known before departure are entered here">
          <form id="duration-form" className="form-stack" onSubmit={submit}>
            <label>Assigned vehicle<select required value={vehicleId} onChange={(event) => setVehicleId(event.target.value)}><option value="">Choose a vehicle</option>{vehicles.map((row) => <option key={row.vehicleId} value={row.vehicleId}>Vehicle {row.vehicleId}</option>)}</select></label>
            <div className="form-grid">
              <label>Planned distance (km)<input required type="number" min="0.1" max="5000" step="0.1" value={plannedDistanceKm} onChange={(event) => setDistance(event.target.value)} /></label>
              <label>Gross vehicle weight<select required value={weight} onChange={(event) => setWeight(event.target.value)}>{(options.data?.weights || []).map((value) => <option key={value} value={value}>{Number(value).toLocaleString()} kg</option>)}</select></label>
              <label>Total mass with trailer<select required value={mass} onChange={(event) => setMass(event.target.value)}>{(options.data?.masses || []).map((value) => <option key={value} value={value}>{Number(value).toLocaleString()} kg</option>)}</select></label>
              <label>Axle class<select required value={axle} onChange={(event) => setAxle(event.target.value)}>{(options.data?.axles || []).map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            </div>
            <label>Planned departure date and time<input required type="datetime-local" value={departureAt} onChange={(event) => setDepartureAt(event.target.value)} /></label>
            <div className="context-note"><strong>Operational context used:</strong> assigned vehicle, vehicle specifications, planned distance, and departure calendar. Route type is not an input in the saved regression recipe.</div>
            <button className="button button-primary button-full" type="submit" disabled={!available || submitting}>{submitting ? 'Estimating…' : 'Estimate tour duration'}</button>
          </form>
        </Panel>
        <div className="side-stack">
          <Panel title="Prediction result" detail="Estimated elapsed tour span">
            {error ? <div className="notice notice-red">{error}</div> : null}
            {result ? (
              <div className="prediction-result">
                <span>EXPECTED ELAPSED SPAN</span>
                <strong>{formatHours(result.predictedDurationHours)}</strong>
                <small>{result.modelName} · {result.version}</small>
                {result.warnings?.length ? <ul className="warning-list">{result.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : null}
                <p>{result.distanceFeatureNote}</p>
                <p>Holdout mean absolute error: {result.holdoutMetrics?.maeHours?.toFixed(2)} hours. This is an average error measure, not a confidence interval.</p>
              </div>
            ) : <div className="prediction-placeholder"><div className="placeholder-mark">h</div><strong>No estimate yet</strong><span>Enter a hypothetical tour and choose “Estimate tour duration.”</span></div>}
          </Panel>
          <Panel title="Model readiness" detail="Chronological holdout snapshot">
            {metadata.data?.available ? <div className="model-stat-list"><div><span>Training episodes</span><strong>{Number(metadata.data.trainingExamples).toLocaleString()}</strong></div><div><span>Holdout episodes</span><strong>{Number(metadata.data.holdoutMetrics?.holdoutEpisodes).toLocaleString()}</strong></div><div><span>Holdout R²</span><strong>{Number(metadata.data.holdoutMetrics?.r2).toFixed(3)}</strong></div><div><span>Holdout RMSE</span><strong>{Number(metadata.data.holdoutMetrics?.rmseHours).toFixed(2)} h</strong></div></div> : <p className="muted-copy">Model metadata will appear here after training.</p>}
          </Panel>
        </div>
      </div>
      <div className="notice notice-amber"><strong>Proxy limitation.</strong> The historical training field is realized tour distance. The form substitutes the analyst’s planned distance; validate with planned-versus-realized route records before using estimates operationally.</div>
    </div>
  );
}
