export default function AgentsPage() {
  return (
    <section className="page-card-wrap deployment-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="deployment-body">
          <div className="deployment-grid">
            <div className="deploy-card"><span className="deploy-card-title">Deploy</span><span className="deploy-card-value">Online</span></div>
            <div className="deploy-card"><span className="deploy-card-title">Endpoint</span><span className="deploy-card-value">/latest</span></div>
            <div className="deploy-card"><span className="deploy-card-title">Logs</span><span className="deploy-card-value">Active</span></div>
          </div>
        </section>
      </div>
      <div className="page-card-footer">Deploy Model</div>
    </section>
  );
}
