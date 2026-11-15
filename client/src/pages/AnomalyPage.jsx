import { useMemo, useState } from 'react';
import { queryString, useApi } from '../api.js';
import { Badge, EmptyState, ErrorState, formatDate, formatScore, LoadingState, PageHeader, Panel, TableFrame } from '../components/common.jsx';

export default function AnomalyPage({ onOpenTrack, onOpenVehicle }) {
  const [filters, setFilters] = useState({ search: '', status: 'flagged', vehicleId: '', cluster: '', from: '', to: '', page: 1, pageSize: 25 });
  const query = useMemo(() => queryString(filters), [filters]);
  const results = useApi('/api/anomalies?' + query);
  const selectedId = results.data?.items?.[0]?.trackId;
  const detail = useApi(selectedId ? '/api/tracks/' + selectedId : '');
  const data = results.data;
  const firstFlagged = data?.items?.find((item) => item.flagged);

  return (
    <div className="page-stack">
      <PageHeader eyebrow="INVESTIGATE · ISOLATION FOREST" title="Anomaly Monitoring" description="Review scored validation tracks, filter candidates, and open the underlying telemetry record." action={{ label: firstFlagged ? 'Inspect top candidate' : 'No candidate in view', onClick: () => firstFlagged && onOpenTrack(firstFlagged.trackId), disabled: !firstFlagged }} />
      <Panel title="Candidate filters" detail="Filters apply to saved validation predictions; unscored tracks are not included.">
        <div className="filter-grid">
          <label>Track or vehicle ID<input type="search" value={filters.search} placeholder="Search an ID" onChange={(event) => setFilters({ ...filters, search: event.target.value, page: 1 })} /></label>
          <label>Review status<select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value, page: 1 })}><option value="flagged">Flagged candidates</option><option value="unflagged">Other validation tracks</option><option value="all">All scored tracks</option></select></label>
          <label>Cluster<select value={filters.cluster} onChange={(event) => setFilters({ ...filters, cluster: event.target.value, page: 1 })}><option value="">All assigned clusters</option><option value="0">Cluster 0</option><option value="1">Cluster 1</option><option value="2">Cluster 2</option><option value="unassigned">Unassigned</option></select></label>
          <label>Vehicle ID<input inputMode="numeric" value={filters.vehicleId} placeholder="Any vehicle" onChange={(event) => setFilters({ ...filters, vehicleId: event.target.value, page: 1 })} /></label>
          <label>From<input type="date" value={filters.from} onChange={(event) => setFilters({ ...filters, from: event.target.value, page: 1 })} /></label>
          <label>To<input type="date" value={filters.to} onChange={(event) => setFilters({ ...filters, to: event.target.value, page: 1 })} /></label>
        </div>
      </Panel>

      <div className="split-layout">
        <Panel title="Scored tracks" detail={data ? (data.total.toLocaleString() + ' results · threshold ' + formatScore(data.threshold)) : 'Loading results'}>
          {results.loading ? <LoadingState label="Loading validation scores…" /> : results.error ? <ErrorState message={results.error} /> : data?.items?.length ? (
            <>
              <TableFrame label="Anomaly review candidates">
                <thead><tr><th>Track</th><th>Vehicle</th><th>Cluster</th><th>Score</th><th>Start time</th><th>Quality context</th><th>Action</th></tr></thead>
                <tbody>{data.items.map((row) => <tr key={row.trackId} className={row.flagged ? 'row-flagged' : ''}>
                  <td><strong>#{row.trackId}</strong></td><td><button className="text-button" onClick={() => onOpenVehicle(row.vehicleId)}>Vehicle {row.vehicleId}</button></td>
                  <td>{row.clusterId === null ? <Badge>Unassigned</Badge> : <Badge tone={'cluster-' + row.clusterId}>C{row.clusterId}</Badge>}</td>
                  <td><span className={row.flagged ? 'score-high' : ''}>{formatScore(row.score)}</span>{row.flagged ? <small className="cell-note">above review threshold</small> : null}</td>
                  <td>{formatDate(row.startTime)}</td><td>{row.reasons?.length ? row.reasons.join(', ') : row.qualityStatus}</td>
                  <td><button className="button button-small" onClick={() => onOpenTrack(row.trackId)}>Investigate</button></td>
                </tr>)}</tbody>
              </TableFrame>
              <div className="pagination"><button className="button button-quiet" disabled={data.page <= 1} onClick={() => setFilters({ ...filters, page: data.page - 1 })}>Previous</button><span>Page {data.page} of {Math.max(1, Math.ceil(data.total / data.pageSize))}</span><button className="button button-quiet" disabled={data.page * data.pageSize >= data.total} onClick={() => setFilters({ ...filters, page: data.page + 1 })}>Next</button></div>
            </>
          ) : <EmptyState title="No scored tracks match these filters" detail="Try widening the date range or changing the cluster and status." />}
        </Panel>
        <div className="side-stack">
          <Panel title="Frequently flagged vehicles" detail="Counts from the saved validation window">
            {data?.frequentVehicles?.length ? <div className="rank-list">{data.frequentVehicles.slice(0, 8).map((row, index) => <button key={row.vehicleId} onClick={() => onOpenVehicle(row.vehicleId)}><span className="rank">{String(index + 1).padStart(2, '0')}</span><strong>Vehicle {row.vehicleId}</strong><Badge tone="red">{row.flaggedTracks} flags</Badge></button>)}</div> : <EmptyState title="No flagged vehicles" detail="No validation candidates are currently available." />}
          </Panel>
          <Panel title="Selected candidate context" detail="Observed features and quality flags">
            {detail.loading ? <LoadingState label="Loading track detail…" /> : detail.data ? (
              <>
                <div className="candidate-score"><span>Track #{detail.data.track.trackId}</span><strong>{formatScore(detail.data.anomaly?.score)}</strong><small>threshold {formatScore(detail.data.anomaly?.threshold)}</small></div>
                <div className="feature-grid feature-grid-small">
                  {Object.entries(detail.data.features).map(([key, value]) => <div key={key}><span>{key.replace(/[A-Z]/g, (letter) => ' ' + letter).replace(/^./, (letter) => letter.toUpperCase())}</span><strong>{value === null || value === undefined ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></div>)}
                </div>
                <div className="notice notice-slate">{data?.attributionNote || 'Feature values are context; model attribution is unavailable.'}</div>
                {detail.data.quality.reasons.length ? <div className="reason-chips">{detail.data.quality.reasons.map((reason) => <Badge key={reason} tone="amber">{reason}</Badge>)}</div> : <p className="muted-copy">No recorded quality reason codes for this track.</p>}
              </>
            ) : <EmptyState title="Choose a scored track" detail="The highest-scoring visible row is shown here." />}
          </Panel>
        </div>
      </div>
      <div className="notice notice-amber"><strong>Score semantics.</strong> {data?.thresholdMeaning || 'Higher Isolation Forest scores are more unusual, not probabilities.'} A candidate needs analyst review.</div>
    </div>
  );
}
