export default function TasksPage() {
  return (
    <section className="page-card-wrap training-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body">
        <section className="training-body">
          <div className="training-title">Training</div>
          <div className="progress-row">
            <span className="progress-label">Job 01</span>
            <span className="progress-bar"><span className="progress-fill f1"></span></span>
          </div>
          <div className="progress-row">
            <span className="progress-label">Job 02</span>
            <span className="progress-bar"><span className="progress-fill f2"></span></span>
          </div>
          <div className="progress-row">
            <span className="progress-label">Job 03</span>
            <span className="progress-bar"><span className="progress-fill f3"></span></span>
          </div>
        </section>
      </div>
      <div className="page-card-footer">Training</div>
    </section>
  );
}
