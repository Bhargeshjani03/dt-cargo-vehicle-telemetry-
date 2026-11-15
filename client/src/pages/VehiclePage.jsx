import { useEffect, useMemo, useState } from 'react';
import { queryString, useApi } from '../api.js';
import { BarList, TrendChart } from '../components/Charts.jsx';
import { EmptyState, ErrorState, formatCount, formatDate, formatDistance, formatHours, LoadingState, MetricCard, PageHeader, Panel, TableFrame } from '../components/common.jsx';

export default function VehiclePage({ initialVehicleId, onOpenTrack }) {
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState(initialVehicleId || '');
  useEffect(() => { if (initialVehicleId) setSelectedId(String(initialVehicleId)); }, [initialVehicleId]);
  const listQuery = useMemo(() => queryString({ search, pageSize: 40 }), [search]);
  const list = useApi('/api/vehicles?' + listQuery);
  const detail = useApi(selectedId ? '/api/vehicles/' + selectedId : '');
  const item = detail.data;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="INVESTIGATE · VEHICLE HISTORY" title="Vehicle Explorer" description="Find a vehicle, compare its historical activity, and open individual tracks for review." action={{ label: item?.recentTracks?.[0] ? 'Open recent track' : 'Select a vehicle', onClick: () => item?.recentTracks?.[0] && onOpenTrack(item.recentTracks[0].trackId), disabled: !item?.recentTracks?.[0] }} />
      <Panel title="Search vehicles" detail="Search by saved vehicle ID">
        <label className="search-field"><span>Vehicle ID</span><input type="search" value={search} placeholder="Enter a vehicle number" onChange={(event) => setSearch(event.target.value)} /></label>
        {list.loading ? <LoadingState label="Loading vehicle index…" /> : list.error ? <ErrorState message={list.error} /> : list.data?.items?.length ? (
          <div className="vehicle-pick-list">{list.data.items.map((row) => <button key={row.vehicleId} className={'vehicle-pick ' + (String(row.vehicleId) === String(selectedId) ? 'is-selected' : '')} onClick={() => setSelectedId(String(row.vehicleId))} aria-pressed={String(row.vehicleId) === String(selectedId)}><strong>Vehicle {row.vehicleId}</strong><span>{formatCount(row.tracks)} tracks · {formatDistance(row.distanceKm, 0)}</span><small>{row.flaggedTracks ? row.flaggedTracks + ' validation flags' : 'No saved validation flags'}</small></button>)}</div>
        ) : <EmptyState title="No vehicle matches" detail="Search by a vehicle ID found in the processed track table." />}
      </Panel>

      {detail.loading ? <LoadingState label="Loading selected vehicle history…" /> : detail.error ? <ErrorState message={detail.error} /> : item ? (
        <>
          <div className="section-title-row"><div><div className="eyebrow">SELECTED VEHICLE</div><h2>Vehicle {item.vehicle.vehicleId}</h2></div><span className="source-tag">Historical tracks</span></div>
          <section className="metric-grid">
            <MetricCard label="Tracks" value={formatCount(item.metrics.tracks)} detail={formatCount(item.metrics.tours) + ' distinct tour IDs'} />
            <MetricCard label="Recorded distance" value={formatDistance(item.metrics.distanceKm, 0)} detail="Non-negative processed track distances" />
            <MetricCard label="Recorded track time" value={formatHours(item.metrics.durationHours)} detail="Sum of valid track duration fields" />
            <MetricCard label="Flagged validation tracks" value={formatCount(item.metrics.flaggedTracks)} detail={formatCount(item.metrics.validationTracks) + ' scored tracks'} />
          </section>

          <div className="dashboard-grid">
            <Panel title="Activity over time" detail="Tracks started each month">
              <TrendChart items={item.monthly} valueKey="tracks" valueLabel="tracks" label={'Monthly activity for vehicle ' + item.vehicle.vehicleId} />
            </Panel>
            <Panel title="Saved episode clusters" detail="Distinct assigned episodes containing this vehicle">
              {item.clusters.length ? <BarList items={item.clusters.map((row) => ({ key: row.cluster, label: 'Cluster ' + row.cluster, value: row.episodes, color: ['var(--amber)', 'var(--blue)', 'var(--green)'][row.cluster] }))} /> : <EmptyState title="No saved cluster assignment" detail="This vehicle has no track mapped to an assigned 12-hour episode." />}
            </Panel>
          </div>

          <Panel title="Vehicle specifications" detail="Most recently recorded processed values">
            <div className="spec-list"><div><span>Gross vehicle weight</span><strong>{item.vehicle.grossVehicleWeight ?? '—'}</strong></div><div><span>Total mass with trailer</span><strong>{item.vehicle.totalMassWithTrailer ?? '—'}</strong></div><div><span>Axle class</span><strong>{item.vehicle.axleClass ?? '—'}</strong></div></div>
          </Panel>

          <Panel title="Recent tracks" detail="Open a track to inspect speed, stops, quality warnings, and any validation score">
            <TableFrame label="Recent tracks for selected vehicle">
              <thead><tr><th>Track</th><th>Start</th><th>Cluster</th><th>Distance</th><th>Duration</th><th>Average speed</th><th>Quality</th><th></th></tr></thead>
              <tbody>{item.recentTracks.map((row) => <tr key={row.trackId}><td>#{row.trackId}</td><td>{formatDate(row.startTime)}</td><td>{row.clusterId === null ? 'Unassigned' : 'Cluster ' + row.clusterId}</td><td>{formatDistance(row.distanceKm)}</td><td>{row.durationMinutes === null ? '—' : Number(row.durationMinutes).toFixed(1) + ' min'}</td><td>{row.avgSpeedKmh === null ? '—' : Number(row.avgSpeedKmh).toFixed(1) + ' km/h'}</td><td>{row.qualityStatus}</td><td><button className="button button-small" onClick={() => onOpenTrack(row.trackId)}>Open track</button></td></tr>)}</tbody>
            </TableFrame>
          </Panel>
        </>
      ) : <EmptyState title="Select a vehicle" detail="Choose a vehicle above to load specifications and historical activity." />}
    </div>
  );
}
