export function BarList({ items = [], onSelect, active }) {
  const max = Math.max(1, ...items.map((item) => Number(item.value) || 0));
  return (
    <div className="bar-list">
      {items.map((item) => {
        const row = (
          <>
            <span className="bar-label">{item.label}</span>
            <span className="bar-track"><span className="bar-fill" style={{ width: Math.max(2, (Number(item.value || 0) / max) * 100) + '%', backgroundColor: item.color || 'var(--amber)' }} /></span>
            <strong className="bar-value">{Number(item.value || 0).toLocaleString()}</strong>
          </>
        );
        return onSelect ? (
          <button className={'bar-row bar-button ' + (active === item.key ? 'is-active' : '')} key={item.key ?? item.label} onClick={() => onSelect(item.key)} aria-pressed={active === item.key}>
            {row}
          </button>
        ) : <div className="bar-row" key={item.key ?? item.label}>{row}</div>;
      })}
    </div>
  );
}

export function TrendChart({ items = [], valueKey = 'tracks', valueLabel = 'tracks', color = '#f0b84e', label = 'Activity by month' }) {
  const values = items.map((item) => Number(item[valueKey]) || 0);
  if (!values.length) return <div className="chart-empty">No dated activity for this selection.</div>;
  const max = Math.max(1, ...values);
  const points = values.map((value, index) => {
    const x = values.length === 1 ? 50 : 24 + (index / (values.length - 1)) * 952;
    const y = 152 - (value / max) * 118;
    return x + ',' + y;
  }).join(' ');
  return (
    <div className="trend-wrap">
      <svg className="trend-chart" viewBox="0 0 1000 180" role="img" aria-label={label + ', ' + items.length + ' monthly values'}>
        <line x1="24" y1="154" x2="976" y2="154" className="chart-axis" />
        <polyline points={points} fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        {items.map((item, index) => {
          const x = values.length === 1 ? 50 : 24 + (index / (values.length - 1)) * 952;
          const y = 152 - (values[index] / max) * 118;
          return <circle key={item.month} cx={x} cy={y} r="5" fill={color}><title>{item.month}: {Number(item[valueKey] || 0).toLocaleString()} {valueLabel}</title></circle>;
        })}
      </svg>
      <div className="trend-labels"><span>{items[0].month}</span><strong>Monthly {valueLabel}</strong><span>{items[items.length - 1].month}</span></div>
    </div>
  );
}

export function SpeedChart({ points = [] }) {
  if (!points.length) return <div className="chart-empty">Raw speed telemetry is not available for this track.</div>;
  const values = points.map((point) => Number(point.speedKmh) || 0);
  const max = Math.max(1, ...values);
  const coordinates = values.map((value, index) => {
    const x = values.length === 1 ? 20 : 20 + (index / (values.length - 1)) * 960;
    const y = 150 - (value / max) * 124;
    return x + ',' + y;
  }).join(' ');
  return (
    <div className="speed-chart-wrap">
      <svg className="speed-chart" viewBox="0 0 1000 170" role="img" aria-label={'Track speed over time. Maximum shown ' + max.toFixed(1) + ' kilometres per hour.'}>
        <line x1="20" y1="152" x2="980" y2="152" className="chart-axis" />
        <polyline points={coordinates} fill="none" stroke="var(--blue)" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round" />
        {points.filter((_, index) => index % Math.max(1, Math.floor(points.length / 12)) === 0).map((point, index) => <circle key={index} cx={20 + (points.indexOf(point) / Math.max(1, points.length - 1)) * 960} cy={150 - ((Number(point.speedKmh) || 0) / max) * 124} r="3.5" fill="var(--blue)"><title>{new Date(point.time).toLocaleTimeString()}: {Number(point.speedKmh).toFixed(1)} km/h</title></circle>)}
      </svg>
      <div className="chart-scale"><span>0 km/h</span><span>{max.toFixed(0)} km/h maximum</span></div>
    </div>
  );
}
