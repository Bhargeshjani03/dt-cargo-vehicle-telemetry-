
export default function PlaceholderPage({ title, description }) {
  return (
    <section className="placeholder-page">
      <span className="eyebrow">DT-CARGO / WORKSPACE</span>
      <h1>{title}</h1>
      <p>{description}</p>

      <div className="placeholder-panel">
        <div className="placeholder-icon">◈</div>
        <h3>Workspace under development</h3>
        <p>
          This section will contain the project's actual datasets,
          analysis, visualizations and results.
        </p>
      </div>
    </section>
  );
}
