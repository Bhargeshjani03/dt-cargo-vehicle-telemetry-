import { useEffect, useMemo, useState } from 'react';
import { queryString, useApi } from '../api.js';
import { SpeedChart } from '../components/Charts.jsx';
import { Badge, EmptyState, ErrorState, formatDate, formatDistance, formatScore, LoadingState, PageHeader, Panel, TableFrame } from '../components/common.jsx';

export default function TrackPage({ initialTrackId }) {
  const [search, setSearch] = useState(initialTrackId || '');
  const [submitted, setSubmitted] = useState(initialTrackId || '');
  const [selectedId, setSelectedId] = useState(initialTrackId || '');
  const [filters, setFilters] = useState({ cluster: '', qualityStatus: '', anomalyStatus: '' });
  useEffect(() => {
    if (initialTrackId) {
      setSearch(String(initialTrackId));
      setSubmitted(String(initialTrackId));
      setSelectedId(String(initialTrackId));
    }
  }, [initialTrackId]);
  const query = useMemo(() => queryString({ search: submitted, ...filters, pageSize: 25 }), [submitted, filters]);
  const results = useApi('/api/tracks?' + query);
  const detail = useApi(selectedId ? '/api/tracks/' + selectedId : '');
  const telemetry = useApi(selectedId ? '/api/tracks/' + selectedId + '/telemetry' : '');

  return (
    <div className="page-stack">
      <PageHeader eyebrow="INVESTIGATE · TRACK DETAIL" title="Track Explorer" description="Search by track or vehicle ID, inspect derived features, and compare a record with its saved cluster profile." action={{ label: 'Load track details', onClick: () => { setSubmitted(search.trim()); setSelectedId(search.trim()); }, disabled: !search.trim() }} />
      <Panel title="Track search and filters" detail="Results use processed tracks and saved validation scores">
        <div className="filter-grid filter-grid-track">
          <label>Track ID or Vehicle ID<input inputMode="numeric" value={search} placeholder="Search a numeric ID" onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter') { setSubmitted(search.trim()); setSelectedId(''); } }} /></label>
          <label>Saved cluster<select value={filters.cluster} onChange={(event) => setFilters({ ...filters, cluster: event.target.value })}><option value="">All</option><option value="0">Cluster 0</option><option value="1">Cluster 1</option><option value="2">Cluster 2</option><option value="unassigned">Unassigned</option></select></label>
          <label>Quality status<select value={filters.qualityStatus} onChange={(event) => setFilters({ ...filters, qualityStatus: event.target.value })}><option value="">All statuses</option><option value="eligible">Eligible</option><option value="eligible_with_warnings">Eligible with warnings</option><option value="ineligible">Ineligible</option></select></label>
          <label>Anomaly status<select value={filters.anomalyStatus} onChange={(event) => setFilters({ ...filters, anomalyStatus: event.target.value })}><option value="">Any</option><option value="flagged">Flagged candidates</option><option value="unflagged">Other scored tracks</option></select></label>
          <button className="button button-primary" onClick={() => { setSubmitted(search.trim()); setSelectedId(''); }}>Search tracks</button>
        </div>
      </Panel>

      <div className="dashboard-grid track-layout">
        <Panel title="Matching tracks" detail={results.data ? results.data.total.toLocaleString() + ' results' : 'Search the processed track table'}>
          {results.loading ? <LoadingState label="Searching tracks…" /> : results.error ? <ErrorState message={results.error} /> : results.data?.items?.length ? (
            <div className="track-result-list">{results.data.items.map((row) => <button className={'track-result ' + (String(row.trackId) === String(selectedId) ? 'is-selected' : '')} key={row.trackId} onClick={() => setSelectedId(String(row.trackId))} aria-pressed={String(row.trackId) === String(selectedId)}><span><strong>Track #{row.trackId}</strong><small>Vehicle {row.vehicleId} · {formatDate(row.startTime)}</small></span><span className="track-result-meta"><span>{formatDistance(row.distanceKm)}</span><span>{row.clusterId === null ? 'Unassigned' : 'Cluster ' + row.clusterId}</span></span></button>)}</div>
          ) : <EmptyState title="No tracks match these filters" detail="Try a track ID, vehicle ID, or wider filters." />}
        </Panel>

        <Panel title={detail.data ? 'Track #' + detail.data.track.trackId : 'Track detail'} detail="Processed record with raw speed playback data">
          {detail.loading ? <LoadingState label="Loading track detail…" /> : detail.error ? <ErrorState message={detail.error} /> : detail.data ? (
            <>
              <div className="track-detail-top"><div><span>Vehicle {detail.data.track.vehicleId}</span><strong>{formatDate(detail.data.track.startTime)}</strong></div><div>{detail.data.track.clusterId === null ? <Badge>Unassigned</Badge> : <Badge tone={'cluster-' + detail.data.track.clusterId}>Cluster {detail.data.track.clusterId}</Badge>}</div></div>
              <div className="track-stat-grid"><div><span>Distance</span><strong>{formatDistance(detail.data.track.distanceKm)}</strong></div><div><span>Duration</span><strong>{detail.data.features.durationMinutes === null ? '—' : Number(detail.data.features.durationMinutes).toFixed(1) + ' min'}</strong></div><div><span>Average speed</span><strong>{detail.data.track.avgSpeedKmh === null ? '—' : Number(detail.data.track.avgSpeedKmh).toFixed(1) + ' km/h'}</strong></div><div><span>Stop episodes</span><strong>{detail.data.features.stopEpisodeCount03 ?? '—'}</strong></div></div>
              <div className="quality-line"><span>Extended model eligibility</span><Badge tone={detail.data.quality.extendedStatus === 'ineligible' ? 'red' : detail.data.quality.extendedStatus === 'eligible_with_warnings' ? 'amber' : 'green'}>{detail.data.quality.extendedStatus}</Badge></div>
              {detail.data.anomaly ? <div className="quality-line"><span>Validation anomaly score</span><strong>{formatScore(detail.data.anomaly.score)} {detail.data.anomaly.flagged ? '· review candidate' : '· below threshold'}</strong></div> : <div className="quality-line"><span>Anomaly score</span><span>Not scored in saved validation set</span></div>}
              <div className="quality-line"><span>Telemetry coverage</span><strong>{detail.data.quality.coverageRatio === null ? '—' : (Number(detail.data.quality.coverageRatio) * 100).toFixed(1) + '%'}</strong></div>
              {detail.data.quality.reasons.length ? <div className="reason-chips">{detail.data.quality.reasons.map((reason) => <Badge key={reason} tone="amber">{reason}</Badge>)}</div> : null}
            </>
          ) : <EmptyState title="Choose a track" detail="Select a result to see speed, stops, quality, and anomaly context." />}
        </Panel>
      </div>

      {detail.data ? (
        <div className="dashboard-grid">
          <Panel title="Raw speed profile" detail={telemetry.data ? telemetry.data.source : 'Raw samples converted from m/s to km/h'}>
            {telemetry.loading ? <LoadingState label="Loading raw speed samples…" /> : telemetry.error ? <ErrorState message={telemetry.error} /> : <SpeedChart points={telemetry.data?.points || []} />}
            <p className="panel-note">Stop episodes are derived from the track-level stop feature. The chart uses a bounded sample of raw telemetry points.</p>
          </Panel>
          <Panel title="Observed movement features" detail="Values used by the extended anomaly model">
            {detail.data ? <div className="feature-grid">{Object.entries(detail.data.features).map(([key, value]) => <div key={key}><span>{key.replace(/[A-Z]/g, (letter) => ' ' + letter).replace(/^./, (letter) => letter.toUpperCase())}</span><strong>{value === null || value === undefined ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}</strong></div>)}</div> : null}
            <div className="compare-card"><div className="eyebrow">CLUSTER COMPARISON</div>{detail.data?.typicalCluster ? <p>This track’s distance, duration, speed, and stop count can be compared with cluster medians shown on the Behaviour Clusters page. Model features are context, not per-feature anomaly attribution.</p> : <p>This track is not mapped to a saved 12-hour episode, so a cluster median is unavailable.</p>}</div>
          </Panel>
        </div>
      ) : null}

      <Panel title="Track results" detail="Search results remain available for comparison">
        {results.data?.items?.length ? <TableFrame label="Track search results"><thead><tr><th>Track</th><th>Vehicle</th><th>Cluster</th><th>Distance</th><th>Duration</th><th>Quality</th><th>Anomaly</th></tr></thead><tbody>{results.data.items.map((row) => <tr key={row.trackId}><td>#{row.trackId}</td><td>{row.vehicleId}</td><td>{row.clusterId === null ? 'Unassigned' : row.clusterId}</td><td>{formatDistance(row.distanceKm)}</td><td>{row.durationMinutes === null ? '—' : Number(row.durationMinutes).toFixed(1) + ' min'}</td><td>{row.qualityStatus}</td><td>{row.isAnomaly === null ? 'Not scored' : row.isAnomaly ? 'Flagged' : 'Below threshold'}</td></tr>)}</tbody></TableFrame> : <EmptyState title="No results loaded" detail="Search for a track to compare records." />}
      </Panel>
    </div>
  );
}
