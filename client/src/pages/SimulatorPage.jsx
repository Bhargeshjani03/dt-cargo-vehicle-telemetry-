import { useEffect, useState } from 'react';
import { Pause, Play, RotateCcw } from 'lucide-react';
import { useApi } from '../api.js';
import { formatCount, PageHeader, Panel } from '../components/common.jsx';

const checkpoints = ['Dispatch', 'Checkpoint', 'Weigh station', 'Delivery'];

export default function SimulatorPage() {
  const clusters = useApi('/api/clusters');
  const [cluster, setCluster] = useState(0);
  const [step, setStep] = useState(0);
  const [running, setRunning] = useState(false);
  const [xp, setXp] = useState(0);
  const done = step >= checkpoints.length - 1;

  useEffect(() => {
    if (!running || done) return undefined;
    const timer = window.setInterval(() => {
      setStep((current) => {
        const next = Math.min(checkpoints.length - 1, current + 1);
        setXp(next * 125);
        if (next >= checkpoints.length - 1) setRunning(false);
        return next;
      });
    }, 1900);
    return () => window.clearInterval(timer);
  }, [running, done]);

  function reset() {
    setRunning(false);
    setStep(0);
    setXp(0);
  }

  const progress = step / (checkpoints.length - 1);
  const x = 84 + progress * 730;
  const action = { label: running ? 'Pause simulation' : done ? 'Run contract again' : 'Start contract', onClick: () => done ? reset() : setRunning((value) => !value) };

  return (
    <div className="page-stack">
      <PageHeader eyebrow="SIMULATION · LOCAL SCENARIO" title="Mission Simulator" description="Run an illustrative dispatch contract with checkpoints and local session scoring." action={action} />
      <div className="sim-layout">
        <Panel title="Route contract" detail="Illustrative route schematic · no GPS playback">
          <div className="route-map">
            <div className="route-grid" />
            <svg viewBox="0 0 900 260" role="img" aria-label={'Illustrative route progress: ' + Math.round(progress * 100) + ' percent'}>
              <path d="M80 170 C170 170 150 75 270 75 S390 190 490 150 S620 50 720 98 S790 180 835 180" className="route-line route-line-base" />
              <path d="M80 170 C170 170 150 75 270 75 S390 190 490 150 S620 50 720 98 S790 180 835 180" className="route-line route-line-progress" style={{ strokeDasharray: '1200', strokeDashoffset: String(1200 - 1200 * progress) }} />
              {checkpoints.map((name, index) => {
                const positions = [[80, 170], [270, 75], [490, 150], [835, 180]][index];
                return <g key={name}><circle cx={positions[0]} cy={positions[1]} r={index <= step ? 13 : 9} className={index <= step ? 'route-node route-node-active' : 'route-node'} /><text x={positions[0]} y={positions[1] - 24} textAnchor="middle">{name}</text></g>;
              })}
              <g transform={'translate(' + x + ' 122)'} className="route-truck"><rect x="-18" y="-11" width="32" height="17" rx="4" /><path d="M14 -6h11l8 9v3H14z" /><circle cx="-8" cy="10" r="5" /><circle cx="24" cy="10" r="5" /></g>
            </svg>
          </div>
          <div className="route-checkpoints">{checkpoints.map((name, index) => <div key={name} className={index <= step ? 'checkpoint-done' : ''}><span>{String(index + 1).padStart(2, '0')}</span><strong>{name}</strong></div>)}</div>
          <div className="notice notice-amber"><strong>Simulation only.</strong> Checkpoint placement, route geometry, distance, and mission score are illustrative. The project has no route coordinates.</div>
        </Panel>
        <div className="side-stack">
          <Panel title="Mission briefing" detail="Cluster-backed scenario context">
            <label className="form-label">Select assigned cluster<select value={cluster} onChange={(event) => setCluster(Number(event.target.value))}>{(clusters.data?.profiles || [0, 1, 2].map((value) => ({ cluster: value }))).map((row) => <option key={row.cluster} value={row.cluster}>Cluster {row.cluster} · {formatCount(row.episodes || 0)} episodes</option>)}</select></label>
            <div className="mission-brief"><span>CONTRACT STATUS</span><strong>{done ? 'DELIVERED' : running ? 'IN PROGRESS' : 'READY TO DISPATCH'}</strong><small>Cluster {cluster} · illustrative local run</small></div>
            <div className="xp-card"><span>SESSION XP</span><strong>{xp.toLocaleString()}</strong><small>Local simulation score only</small></div>
            <div className="sim-controls"><button className="button button-primary" onClick={action.onClick}>{running ? <Pause size={16} /> : <Play size={16} />}{action.label}</button><button className="button button-quiet" onClick={reset}><RotateCcw size={16} />Reset</button></div>
          </Panel>
          <Panel title="Selected group" detail="Saved 12-hour episode profile">
            {clusters.data?.profiles?.find((item) => item.cluster === cluster) ? <div className="spec-list"><div><span>Episodes</span><strong>{formatCount(clusters.data.profiles[cluster].episodes)}</strong></div><div><span>Vehicles</span><strong>{formatCount(clusters.data.profiles[cluster].vehicles)}</strong></div><div><span>Median distance</span><strong>{Number(clusters.data.profiles[cluster].medianDistanceKm).toFixed(1)} km</strong></div><div><span>Median speed</span><strong>{Number(clusters.data.profiles[cluster].medianSpeedKmh).toFixed(1)} km/h</strong></div></div> : <p className="muted-copy">Cluster profile loading.</p>}
          </Panel>
        </div>
      </div>
    </div>
  );
}
