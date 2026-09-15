import React from 'react';
import VoiceInput from '../components/voice/VoiceInput.jsx';
import VoiceOutput from '../components/voice/VoiceOutput.jsx';

/* ---- small inline SVG icons ---- */
const ModelIcon = () => (
  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#3b82f6" strokeWidth="2">
    <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
  </svg>
);

const TrainingIcon = () => (
  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#10b981" strokeWidth="2">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
  </svg>
);

const DatasetIcon = () => (
  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#8b5cf6" strokeWidth="2">
    <ellipse cx="12" cy="5" rx="9" ry="3"/>
    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
  </svg>
);

const UsersIcon = () => (
  <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="#f59e0b" strokeWidth="2">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
    <circle cx="9" cy="7" r="4"/>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
  </svg>
);

/* Activity items from the image */
const activityItems = [
  {
    id: 1,
    icon: '🧠',
    cls: 'model',
    title: 'Model training completed',
    desc: 'llama-3-8b-finetuned',
    time: '2h ago',
  },
  {
    id: 2,
    icon: '📤',
    cls: 'upload',
    title: 'New dataset uploaded',
    desc: 'customer-support-qa',
    time: '4h ago',
  },
  {
    id: 3,
    icon: '✅',
    cls: 'eval',
    title: 'Evaluation finished',
    desc: 'gpt-4o-eval',
    time: '5h ago',
  },
  {
    id: 4,
    icon: '🚀',
    cls: 'deploy',
    title: 'Deployment successful',
    desc: 'chat-assistant-v1',
    time: '6h ago',
  },
];

/* System status items */
const statusItems = [
  { name: 'API Server', status: 'Healthy' },
  { name: 'Database',   status: 'Healthy' },
  { name: 'Redis',      status: 'Healthy' },
  { name: 'GPU Workers',status: 'Healthy' },
  { name: 'Storage',    status: 'Healthy' },
];

export default function HomePage() {
  return (
    <div className="page-content-wrapper dashboard-view">

      {/* ---- Header ---- */}
      <div className="dash-header">
        <div>
          <h2>Welcome back, John!</h2>
          <p className="dash-subtitle">Your AI platform is running smoothly. Here's what's happening today.</p>
        </div>
      </div>

      {/* ---- Stats Grid (4 cards) ---- */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Total Models</span>
            <div className="stat-icon-wrap blue"><ModelIcon /></div>
          </div>
          <div className="stat-value">12</div>
          <div className="stat-change up">+2 this week</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Training Jobs</span>
            <div className="stat-icon-wrap green"><TrainingIcon /></div>
          </div>
          <div className="stat-value">3</div>
          <div className="stat-change running">● Running</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Datasets</span>
            <div className="stat-icon-wrap purple"><DatasetIcon /></div>
          </div>
          <div className="stat-value">8</div>
          <div className="stat-change up">+1 this week</div>
        </div>

        <div className="stat-card">
          <div className="stat-top">
            <span className="stat-label">Active Users</span>
            <div className="stat-icon-wrap orange"><UsersIcon /></div>
          </div>
          <div className="stat-value">5</div>
          <div className="stat-change up">+2 this week</div>
        </div>
      </div>

      <div className="dash-card">
        <h3>Voice Route Demo</h3>
        <VoiceInput />
        <VoiceOutput />
      </div>

      {/* ---- Bottom 2-column layout ---- */}
      <div className="dashboard-bottom">

        {/* ---- Left column: Recent Activity + System Status ---- */}
        <div className="activity-status-col">

          {/* Recent Activity */}
          <div className="dash-card">
            <h3>Recent Activity</h3>
            <ul className="activity-list">
              {activityItems.map((item) => (
                <li key={item.id} className="activity-item">
                  <div className={`act-icon ${item.cls}`}>{item.icon}</div>
                  <div className="act-body">
                    <div className="act-title">{item.title}</div>
                    <div className="act-desc">{item.desc}</div>
                  </div>
                  <div className="act-time">{item.time}</div>
                </li>
              ))}
            </ul>
          </div>

          {/* System Status */}
          <div className="dash-card">
            <h3>System Status</h3>
            <ul className="status-list">
              {statusItems.map((item) => (
                <li key={item.name} className="status-row">
                  <span className="status-name">{item.name}</span>
                  <span className="status-badge healthy">{item.status}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* ---- Right column: Usage Overview ---- */}
        <div className="usage-col">
          <div className="dash-card" style={{ flex: 1 }}>
            <div className="usage-header">
              <h3>Usage Overview</h3>
              <span className="usage-period">Last 7 days</span>
            </div>

            {/* SVG Area Chart exactly like the image */}
            <div style={{ marginTop: 8 }}>
              {/* Y-axis labels */}
              <div style={{ display: 'flex', alignItems: 'stretch', height: 200 }}>
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  paddingRight: 8,
                  paddingBottom: 20,
                  fontSize: 11,
                  color: '#94a3b8',
                }}>
                  {['80', '60', '40', '20', '0'].map(v => <span key={v}>{v}</span>)}
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                  <svg
                    viewBox="0 0 400 160"
                    preserveAspectRatio="none"
                    style={{ flex: 1, width: '100%' }}
                  >
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#2d4fd7" stopOpacity="0.35" />
                        <stop offset="100%" stopColor="#2d4fd7" stopOpacity="0.02" />
                      </linearGradient>
                    </defs>
                    {/* Grid lines */}
                    {[0, 40, 80, 120, 160].map(y => (
                      <line key={y} x1="0" y1={y} x2="400" y2={y}
                        stroke="#e2e8f0" strokeWidth="0.8" strokeDasharray="4,4"/>
                    ))}
                    {/* Area fill */}
                    <path
                      d="M0,120 C20,115 40,100 70,90 C100,80 120,130 150,100 C180,70 200,60 230,40 C260,20 280,50 310,30 C340,10 370,45 400,20 L400,160 L0,160 Z"
                      fill="url(#areaGrad)"
                    />
                    {/* Line */}
                    <path
                      d="M0,120 C20,115 40,100 70,90 C100,80 120,130 150,100 C180,70 200,60 230,40 C260,20 280,50 310,30 C340,10 370,45 400,20"
                      fill="none"
                      stroke="#2d4fd7"
                      strokeWidth="2.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                  {/* X-axis labels */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 11,
                    color: '#94a3b8',
                    paddingTop: 6,
                  }}>
                    {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d => (
                      <span key={d}>{d}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  );
}
