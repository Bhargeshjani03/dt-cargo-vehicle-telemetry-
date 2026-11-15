import { useApi } from '../api.js';
import { EmptyState, ErrorState, formatCount, formatScore, LoadingState, PageHeader, Panel } from '../components/common.jsx';

export default function MethodologyPage({ onNavigate }) {
  const state = useApi('/api/methodology');
  const data = state.data;
  const anomaly = data?.anomaly;
  const regression = data?.regression;

  return (
    <div className="page-stack">
      <PageHeader eyebrow="MODEL TRANSPARENCY · HOW TO READ RESULTS" title="Model Insights & Methodology" description="Review model inputs, evaluation summaries, operating limits, and the meaning of each score." action={{ label: 'Review data eligibility', onClick: () => onNavigate('quality') }} />
      {state.loading ? <LoadingState label="Loading model documentation…" /> : state.error ? <ErrorState message={state.error} /> : data ? (
        <>
          <div className="method-grid">
            <Panel title="Isolation Forest" detail="Unsupervised track-level review model">
              <div className="method-kpis"><div><span>Review threshold</span><strong>{formatScore(anomaly?.threshold)}</strong></div><div><span>Validation tracks</span><strong>{formatCount(anomaly?.validation?.validation_tracks)}</strong></div><div><span>Review candidates</span><strong>{formatCount(anomaly?.validation?.validation_flagged_tracks)}</strong></div></div>
              <p>Score: negative decision_function. Higher values are more unusual; the score is not a probability.</p>
              <div className="feature-chip-list">{(anomaly?.features || []).map((feature) => <span key={feature}>{feature}</span>)}</div>
              <p className="muted-copy">{anomaly?.limitation}</p>
            </Panel>
            <Panel title="Tour duration regression" detail="HistGradientBoosting model with a log-transformed target">
              {regression?.available ? (
                <>
                  <div className="method-kpis"><div><span>Holdout R²</span><strong>{Number(regression.holdoutMetrics.r2).toFixed(3)}</strong></div><div><span>Mean absolute error</span><strong>{Number(regression.holdoutMetrics.maeHours).toFixed(2)} h</strong></div><div><span>Training episodes</span><strong>{formatCount(regression.trainingExamples)}</strong></div></div>
                  <p>Inputs: planned distance, vehicle specifications, departure calendar, and vehicle ID.</p>
                  <p className="muted-copy">{regression.distanceFeatureNote}</p>
                </>
              ) : <EmptyState title="No duration model artifact" detail="The prediction page explains how to train and use the project model." />}
            </Panel>
          </div>
          <Panel title="Saved movement clusters" detail="Three descriptive groups at 12-hour episode grain">
            <div className="pipeline-steps"><div><span>01</span><strong>Track features</strong><small>Distance and speed summaries are aggregated to episode-level records.</small></div><div><span>02</span><strong>Saved assignment</strong><small>{data.clusters.assignmentFile}</small></div><div><span>03</span><strong>Analyst interpretation</strong><small>Cluster IDs describe groups; they are not operational labels.</small></div></div>
            <p>{data.clusters.interpretation}</p>
            <p className="muted-copy">{data.clusters.stopContext}</p>
          </Panel>
          <Panel title="Limits and interpretation" detail="Keep these boundaries visible when sharing results">
            <ul className="limit-list">{(data.limits || []).map((limit) => <li key={limit}>{limit}</li>)}</ul>
            <div className="notice notice-amber"><strong>Review before action.</strong> There are no verified anomaly labels, so alert counts are model review candidates, not measured fault rates.</div>
          </Panel>
        </>
      ) : null}
    </div>
  );
}
