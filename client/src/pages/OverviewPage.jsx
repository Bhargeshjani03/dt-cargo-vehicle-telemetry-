import { lazy, Suspense, useMemo, useState } from 'react';
import { Activity, AlertTriangle, Boxes, Truck } from 'lucide-react';
import { queryString, useApi } from '../api.js';
import { BarList, TrendChart } from '../components/Charts.jsx';
import { EmptyState, ErrorState, formatCount, formatDistance, LoadingState, MetricCard, PageHeader, Panel } from '../components/common.jsx';

const TruckFleetStage = lazy(() => import('../components/TruckFleetStage.jsx'));

export default function OverviewPage({ onNavigate }) {
  const filters = useApi('/api/filters');
  const [range, setRange] = useState({ from: '', to: '', fleetTestId: '' });
  const query = useMemo(() => queryString(range), [range]);
  const view = useApi('/api/overview' + (query ? '?' + query : ''));
  const [selectedCluster, setSelectedCluster] = useState(0);
  const data = view.data;
  const maxVehicleHours = Math.max(1, ...(data?.mostActiveVehicles || []).map((item) => item.durationHours));

  return (
    <div className="page-stack">
      <PageHeader eyebrow="OPERATIONS · HISTORICAL ACTIVITY" title="Fleet Overview" description="Scan recorded fleet movement, saved behaviour groups, and validation-period review candidates." action={{ label: 'Review anomaly candidates', onClick: () => onNavigate('anomalies') }} />
      <div className="filter-toolbar">
        <label>From<input type="date" value={range.from} onChange={(event) => setRange({ ...range, from: event.target.value })} /></label>
        <label>To<input type="date" value={range.to} onChange={(event) => setRange({ ...range, to: event.target.value })} /></label>
        <label>Fleet test group<select value={range.fleetTestId} onChange={(event) => setRange({ ...range, fleetTestId: event.target.value })}><option value="">All groups</option>{(filters.data?.fleetGroups || []).map((group) => <option key={group} value={group}>{group}</option>)}</select></label>
        <button className="button button-quiet" onClick={() => setRange({ from: '', to: '', fleetTestId: '' })}>Clear filters</button>
        <span className="source-tag">{data?.source || filters.data?.source || 'Loading source…'}</span>
      </div>

      {view.loading ? <LoadingState /> : view.error ? <ErrorState message={view.error} /> : data ? (
        <>
          <section className="metric-grid">
            <MetricCard label="Vehicles active" value={formatCount(data.metrics.vehicles)} detail="Unique vehicles with tracks in view" icon={Truck} />
            <MetricCard label="Fleet test groups" value={formatCount(data.metrics.fleetTestGroups)} detail="Distinct fleet_test_id values" icon={Boxes} tone="blue" />
            <MetricCard label="Tracks recorded" value={formatCount(data.metrics.tracks)} detail="Unique processed track records" icon={Activity} tone="green" />
            <MetricCard label="Recorded distance" value={formatDistance(data.metrics.distanceKm, 0)} detail="Sum of valid processed distances" icon={Activity} tone="amber" />
          </section>

          <div className="dashboard-grid dashboard-grid-wide">
            <Panel title="Cluster truck yard" detail="Three realistic truck models, arranged by the saved 12-hour episode cluster. Drag or swipe to rotate." className="yard-panel">
              <Suspense fallback={<div className="stage-loading">Loading the 3D truck yard…</div>}><TruckFleetStage profiles={data.clusters} selectedCluster={selectedCluster} onSelectCluster={setSelectedCluster} height={300} /></Suspense>
              <div className="panel-note">Cluster membership and counts come from saved episode assignments. The 3D scene is a visual fleet view, not a live location map.</div>
            </Panel>
            <Panel title="Review queue" detail="Isolation Forest validation results" className="review-panel">
              <div className="review-stat"><AlertTriangle size={18} aria-hidden="true" /><strong>{formatCount(data.anomalies.flagged)}</strong><span>review candidates</span></div>
              <p className="review-copy">{formatCount(data.anomalies.validationTracks)} scored validation tracks in this date window. The threshold is a 2% review policy, not an anomaly prevalence estimate.</p>
              <button className="button button-primary button-full" onClick={() => onNavigate('anomalies')}>Open review queue</button>
              <div className="review-footnote">{data.anomalies.scope}</div>
            </Panel>
          </div>

          <div className="dashboard-grid">
            <Panel title="Fleet activity" detail="Track starts, active vehicles, and recorded distance by month">
              <TrendChart items={data.monthly} valueKey="tracks" valueLabel="tracks" label="Monthly fleet activity" />
              <div className="compact-stats"><span><strong>{formatCount(data.metrics.assignedTracks)}</strong> tracks mapped to a saved episode</span><span><strong>{formatCount(data.metrics.unassignedTracks)}</strong> unassigned tracks</span></div>
            </Panel>
            <Panel title="Saved episode mix" detail="One count per saved tour episode">
              <BarList items={data.clusterCounts.map((row) => ({ key: row.cluster, label: 'Cluster ' + row.cluster, value: row.episodes, color: ['var(--amber)', 'var(--blue)', 'var(--green)'][row.cluster] }))} onSelect={setSelectedCluster} active={selectedCluster} />
              <p className="panel-note">{data.coverageNote}</p>
            </Panel>
          </div>

          <Panel title="Recorded vehicle activity" detail="Highest recorded active time in this view · not a shift-utilization rate">
            <div className="vehicle-activity-list">{(data.mostActiveVehicles || []).map((vehicle, index) => <div className="vehicle-activity-row" key={vehicle.vehicleId}>
              <span className="rank">{String(index + 1).padStart(2, '0')}</span>
              <div className="vehicle-activity-main"><strong>Vehicle {vehicle.vehicleId}</strong><small>{formatCount(vehicle.tracks)} tracks · {formatDistance(vehicle.distanceKm, 0)}</small></div>
              <div className="vehicle-activity-bar"><span style={{ width: (vehicle.durationHours / maxVehicleHours * 100) + '%' }} /></div>
              <strong className="vehicle-activity-hours">{Number(vehicle.durationHours).toLocaleString()} h</strong>
            </div>)}</div>
          </Panel>

          <Panel title="Operational signals" detail="Generated from the current filters and saved project data">
            <div className="insight-list">{data.insights.map((insight, index) => <div className="insight-row" key={index}><span className="insight-index">0{index + 1}</span><p>{insight}</p></div>)}</div>
          </Panel>
          <div className="notice notice-amber"><strong>Interpret carefully.</strong> Anomaly scores are review signals, not diagnoses. Cluster IDs are descriptive model groups.</div>
        </>
      ) : <EmptyState title="No fleet data found" detail="Check the configured processed CSV files or connect MongoDB." />}
    </div>
  );
}
