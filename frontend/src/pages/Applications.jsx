export default function ApplicationsPage() {
  return (
    <section className="page-card-wrap datasets-page">
      <div className="page-card-head">
        <span className="logo-inline">NOVA AI</span>
        <span className="search-inline">Search</span>
        <span className="icon-inline">✦</span>
      </div>
      <div className="page-card-body dataset-body">
        <aside className="mini-sidebar">
          <span className="mini-sidebar-title">Datasets</span>
          <span className="mini-sidebar-link active">All Datasets</span>
          <span className="mini-sidebar-link">Images</span>
          <span className="mini-sidebar-link">Texts</span>
          <span className="mini-sidebar-link">Files</span>
        </aside>
        <section className="page-card-content-area">
          <div className="page-title-line">
            <span>Datasets</span>
          </div>
          <div className="tables">
            <div className="table-row"><span>Name</span><span>Type</span><span>Status</span></div>
            <div className="table-row"><span>Knowledge</span><span>Text</span><span>Ready</span></div>
            <div className="table-row"><span>Vision</span><span>Image</span><span>Ready</span></div>
            <div className="table-row"><span>Docs</span><span>File</span><span>Queued</span></div>
          </div>
        </section>
      </div>
      <div className="page-card-footer">Datasets</div>
    </section>
  );
}
