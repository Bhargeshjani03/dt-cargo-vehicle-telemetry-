import { lazy, Suspense, useMemo, useState } from 'react';
import { queryString, useApi } from '../api.js';
import { BarList, TrendChart } from '../components/Charts.jsx';
import { EmptyState, ErrorState, formatCount, formatDistance, formatHours, LoadingState, MetricCard, PageHeader, Panel } from '../components/common.jsx';

const TruckFleetStage = lazy(() => import('../components/TruckFleetStage.jsx'));

export default function ClustersPage() {
  const state = useApi('/api/clusters');
  const [selected, setSelected] = useState(0);
  const profile = state.data?.profiles?.find((row) => row.cluster === selected);
  const monthly = useMemo(() => (state.data?.monthly || []).filter((row) => row.cluster === selected), [state.data, selected]);
  const action = { label: 'Inspect Cluster ' + selected, onClick: () => document.getElementById('cluster-profile-details')?.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }) };

  return (
    <div className="page-stack">
      <PageHeader eyebrow="UNDERSTAND · SAVED 12-HOUR ASSIGNMENTS" title="Behaviour Clusters" description="Compare three descriptive movement groups and inspect the saved episode profiles behind each truck bay." action={action} />
      {state.loading ? <LoadingState label="Loading saved cluster assignments…" /> : state.error ? <ErrorState message={state.error} /> : state.data ? (
        <>
          <Panel title="Three clusters. Three trucks." detail="The realistic model is duplicated into separate cluster bays; cluster color marks the assignment, not truck paint.">
            <Suspense fallback={<div className="stage-loading">Loading the 3D truck yard…</div>}><TruckFleetStage profiles={state.data.profiles} selectedCluster={selected} onSelectCluster={setSelected} height={390} /></Suspense>
          </Panel>
          <div className="cluster-card-grid">
            {state.data.profiles.map((row) => <button key={row.cluster} className={'cluster-profile-card cluster-' + row.cluster + (selected === row.cluster ? ' is-selected' : '')} onClick={() => setSelected(row.cluster)} aria-pressed={selected === row.cluster}>
              <span className="cluster-card-top"><span>CLUSTER {row.cluster}</span><strong>{formatCount(row.episodes)} episodes</strong></span>
              <span className="cluster-card-stats"><span>{formatCount(row.vehicles)} vehicles</span><span>Median {formatDistance(row.medianDistanceKm)}</span><span>{formatHours(row.medianElapsedHours)} elapsed span</span></span>
            </button>)}
          </div>
          {profile ? <div id="cluster-profile-details">
            <section className="metric-grid">
              <MetricCard label="Saved episodes" value={formatCount(profile.episodes)} detail="12-hour assignment grain" />
              <MetricCard label="Vehicles" value={formatCount(profile.vehicles)} detail="Distinct vehicle IDs" />
              <MetricCard label="Median distance" value={formatDistance(profile.medianDistanceKm)} detail="Per saved episode" />
              <MetricCard label="Median speed" value={profile.medianSpeedKmh === null ? '—' : Number(profile.medianSpeedKmh).toFixed(1) + ' km/h'} detail="Distance-based episode speed" />
            </section>
            <div className="dashboard-grid">
              <Panel title={'Cluster ' + selected + ' profile'} detail="Medians from the original episode assignments">
                <div className="spec-list">
                  <div><span>Elapsed span</span><strong>{formatHours(profile.medianElapsedHours)}</strong></div>
                  <div><span>Recorded track time</span><strong>{formatHours(profile.medianRecordedHours)}</strong></div>
                  <div><span>Tracks per episode</span><strong>{profile.medianTracksPerEpisode === null ? '—' : Number(profile.medianTracksPerEpisode).toFixed(1)}</strong></div>
                  <div><span>Summed track stop episodes</span><strong>{profile.medianTrackStopEpisodes === null ? '—' : Number(profile.medianTrackStopEpisodes).toFixed(1)}</strong></div>
                </div>
                <p className="panel-note">Stop measure is a sum of track-level stop episodes assigned to the episode; it is not a deduplicated count of unique roadside stops.</p>
              </Panel>
              <Panel title="Episode volume over time" detail="Monthly saved assignments for the selected cluster">
                <TrendChart items={monthly} valueKey="episodes" valueLabel="episodes" label={'Monthly episode assignments for cluster ' + selected} />
              </Panel>
            </div>
          </div> : null}
          <Panel title="Compare episode volume" detail="Tap or click a row to select its cluster bay">
            <BarList items={state.data.profiles.map((row) => ({ key: row.cluster, label: 'Cluster ' + row.cluster, value: row.episodes, color: ['var(--amber)', 'var(--blue)', 'var(--green)'][row.cluster] }))} active={selected} onSelect={setSelected} />
          </Panel>
          <div className="notice notice-slate">Cluster numbers identify model groups, not operating classes. Assignment statistics are episode-level; the 3D route positions are illustrative.</div>
        </>
      ) : <EmptyState title="Saved clusters are unavailable" detail="The processed three-cluster episode assignment file was not found." />}
    </div>
  );
}
