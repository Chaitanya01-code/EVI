export default function SettingsPage() {
  return (
    <section className="page-card-wrap registry-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="registry-body">
          <div className="registry-row"><span>Model</span><span>v1.4.7</span><span>Ready</span></div>
          <div className="registry-row"><span>Vision</span><span>v2.1.0</span><span>Ready</span></div>
          <div className="registry-row"><span>RAG</span><span>v0.9.1</span><span>Draft</span></div>
        </section>
      </div>
      <div className="page-card-footer">Model Registry</div>
    </section>
  );
}
