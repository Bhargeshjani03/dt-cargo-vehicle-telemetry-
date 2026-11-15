import { AlertTriangle, ChevronRight, LoaderCircle } from 'lucide-react';

export function PageHeader({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action ? (
        <div className="heading-action">
          <span>PRIMARY ACTION</span>
          <button className="button button-primary" onClick={action.onClick} disabled={action.disabled}>
            {action.label}<ChevronRight size={16} aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function MetricCard({ label, value, detail, icon: Icon, tone = 'amber' }) {
  return (
    <article className="metric-card" data-reveal>
      <div className={'metric-icon tone-' + tone}>{Icon ? <Icon size={18} aria-hidden="true" /> : null}</div>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value ?? '—'}</div>
      {detail ? <div className="metric-detail">{detail}</div> : null}
    </article>
  );
}

export function LoadingState({ label = 'Loading saved telemetry…' }) {
  return <div className="state-panel" role="status" aria-live="polite"><LoaderCircle className="spin" size={20} aria-hidden="true" />{label}</div>;
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-panel state-error" role="alert">
      <AlertTriangle size={20} aria-hidden="true" />
      <span>{message}</span>
      {onRetry ? <button className="button button-quiet" onClick={onRetry}>Retry</button> : null}
    </div>
  );
}

export function EmptyState({ title, detail }) {
  return <div className="empty-state"><strong>{title}</strong><span>{detail}</span></div>;
}

export function Panel({ title, detail, action, children, className = '' }) {
  return (
    <section className={'panel ' + className} data-reveal>
      {(title || action) ? (
        <header className="panel-heading">
          <div>{title ? <h2>{title}</h2> : null}{detail ? <p>{detail}</p> : null}</div>
          {action || null}
        </header>
      ) : null}
      {children}
    </section>
  );
}

export function Badge({ children, tone = 'neutral' }) {
  return <span className={'badge badge-' + tone}>{children}</span>;
}

export function TableFrame({ children, label }) {
  return <div className="table-scroll" role="region" aria-label={label || 'Scrollable data table'} tabIndex="0"><table>{children}</table></div>;
}

export function formatCount(value) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString();
}

export function formatDistance(value, digits = 1) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }) + ' km';
}

export function formatHours(value) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 }) + ' h';
}

export function formatDate(value) {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatScore(value) {
  return value === null || value === undefined || !Number.isFinite(Number(value)) ? '—' : Number(value).toFixed(4);
}
