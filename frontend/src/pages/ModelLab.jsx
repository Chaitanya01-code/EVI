export default function ModelLabPage() {
  return (
    <section className="page-card-wrap modellab-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="model-lab-grid">
          <div className="model-card"><span className="model-card-title">Model Lab</span><span className="model-card-stat">Ready</span></div>
          <div className="model-card"><span className="model-card-title">Training</span><span className="model-card-stat">12%</span></div>
          <div className="model-card"><span className="model-card-title">Deploy</span><span className="model-card-stat">Online</span></div>
        </section>
      </div>
      <div className="page-card-footer">Model Lab</div>
    </section>
  );
}
