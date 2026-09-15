export default function MemoryPage() {
  return (
    <section className="page-card-wrap experiments-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="experiments-body">
          <table className="experiments-table">
            <thead>
              <tr><th>Experiment</th><th>Status</th><th>Score</th></tr>
            </thead>
            <tbody>
              <tr><td>GPT-Direct</td><td>Running</td><td>91%</td></tr>
              <tr><td>Vision-Lite</td><td>Ready</td><td>88%</td></tr>
              <tr><td>RAG-Rank</td><td>Running</td><td>90%</td></tr>
            </tbody>
          </table>
        </section>
      </div>
      <div className="page-card-footer">Experiments</div>
    </section>
  );
}
