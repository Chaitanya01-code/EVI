export default function ModelsPage() {
  return (
    <section className="page-card-wrap evaluation-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="evaluation-body">
          <div className="score-card">
            <span className="score-label">Evaluation</span>
            <span className="score-value">92.8%</span>
          </div>
          <div className="score-card">
            <span className="score-label">Accuracy</span>
            <span className="score-value">94.2%</span>
          </div>
          <div className="score-card">
            <span className="score-label">Latency</span>
            <span className="score-value">0.8s</span>
          </div>
        </section>
      </div>
      <div className="page-card-footer">Evaluation</div>
    </section>
  );
}
