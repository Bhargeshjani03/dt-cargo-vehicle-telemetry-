import { useMemo, useState } from 'react';
import { queryString, useApi } from '../api.js';
import { EmptyState, ErrorState, formatCount, formatDate, LoadingState, MetricCard, PageHeader, Panel, TableFrame } from '../components/common.jsx';

const explanations = {
  track_gap_missing: 'A track boundary gap value is missing; review segmentation context.',
  avg_speed_gt_max_speed: 'Average speed exceeds the recorded maximum speed; inspect the raw series.',
  insufficient_telemetry: 'There is not enough valid telemetry for the model eligibility rule.',
  duration_invalid: 'Track duration is missing, zero, or otherwise invalid.',
  distance_missing: 'Processed distance is missing.',
  avg_speed_negative: 'A negative average speed value was observed.',
  r_signal_loss_missing: 'Required radio signal-loss information is missing.',
  zero_distance: 'The recorded distance is zero; this is retained for review.',
};

export default function QualityPage({ onOpenTrack }) {
  const summary = useApi('/api/quality');
  const [status, setStatus] = useState('ineligible');
  const query = useMemo(() => queryString({ status, pageSize: 25 }), [status]);
  const records = useApi('/api/quality/records?' + query);
  const data = summary.data;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="DATA TRUST · MODEL ELIGIBILITY" title="Data Quality & Insights" description="Review telemetry coverage, inconsistent records, quality flags, and eligibility for each anomaly model." action={{ label: 'Review ineligible tracks', onClick: () => setStatus('ineligible') }} />
      {summary.loading ? <LoadingState label="Summarizing track quality…" /> : summary.error ? <ErrorState message={summary.error} /> : data ? (
        <>
          <section className="metric-grid">
            <MetricCard label="Tracks assessed" value={formatCount(data.tracks)} detail="Processed track rows" />
            <MetricCard label="Eligible" value={formatCount(data.statusCounts.eligible)} detail="Extended six-feature status" tone="green" />
            <MetricCard label="Eligible with warnings" value={formatCount(data.statusCounts.eligible_with_warnings)} detail="Usable but review context present" tone="amber" />
            <MetricCard label="Ineligible" value={formatCount(data.statusCounts.ineligible)} detail="Extended six-feature status" tone="red" />
          </section>
          <div className="dashboard-grid">
            <Panel title="Required feature completeness" detail="Missing counts in the saved modeling dataset">
              <div className="feature-grid">{Object.entries(data.missingFeatures).map(([key, value]) => <div key={key}><span>{key.replace(/[A-Z]/g, (letter) => ' ' + letter).replace(/^./, (letter) => letter.toUpperCase())}</span><strong>{formatCount(value)} missing</strong></div>)}</div>
            </Panel>
            <Panel title="Common quality flags" detail="Counts by saved reason code">
              <div className="reason-list">{data.reasonCounts.slice(0, 8).map((item) => <div key={item.reason}><span><strong>{item.reason}</strong><small>{explanations[item.reason] || 'Inspect the track context and raw telemetry before acting.'}</small></span><b>{formatCount(item.count)}</b></div>)}</div>
            </Panel>
          </div>

          <Panel title="Review records by model eligibility" detail="Select an eligibility state to browse the matching tracks">
            <label className="inline-filter">Extended model status<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="ineligible">Ineligible</option><option value="eligible_with_warnings">Eligible with warnings</option><option value="eligible">Eligible</option><option value="all">All records</option></select></label>
            {records.loading ? <LoadingState label="Loading quality records…" /> : records.error ? <ErrorState message={records.error} /> : records.data?.items?.length ? <TableFrame label="Data quality records"><thead><tr><th>Track</th><th>Vehicle</th><th>Start time</th><th>Quality status</th><th>Quality flags</th><th></th></tr></thead><tbody>{records.data.items.map((row) => <tr key={row.trackId}><td>#{row.trackId}</td><td>{row.vehicleId}</td><td>{formatDate(row.startTime)}</td><td>{row.qualityStatus}</td><td>{row.reasons?.length ? row.reasons.join(', ') : row.extendedIneligibleReasons?.join(', ') || '—'}</td><td><button className="button button-small" onClick={() => onOpenTrack(row.trackId)}>Inspect</button></td></tr>)}</tbody></TableFrame> : <EmptyState title="No matching records" detail="Choose another eligibility status." />}
          </Panel>
          <div className="notice notice-slate">Eligibility reflects the saved extended-feature model rules. A warning does not automatically make a track unusable; inspect its record before deciding.</div>
        </>
      ) : null}
    </div>
  );
}
