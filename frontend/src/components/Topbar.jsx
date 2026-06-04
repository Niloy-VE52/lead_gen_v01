import { BASE_URL } from "../api/client";

const IconMenu = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M2 4h12M2 8h12M2 12h12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const IconDot = ({ active }) => (
  <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
    <circle cx="4" cy="4" r="3" fill={active ? "#2563eb" : "#98a2b3"}/>
  </svg>
);

export default function Topbar({ runs, sidebarOpen, onToggleSidebar }) {
  const activeCount = runs.filter((r) => r.status === "running").length;

  return (
    <div className="topbar">
      <div className="topbar-left">
        <button className="topbar-toggle" onClick={onToggleSidebar} title="Toggle sidebar">
          <IconMenu />
        </button>
        <div className="topbar-divider" />
        <div>
          <div className="brand-title">LeadGen Pipeline</div>
        </div>
      </div>

      <div className="topbar-right">
        <div className={`topbar-status ${activeCount > 0 ? "active" : ""}`}>
          <IconDot active={activeCount > 0} />
          &nbsp;
          {activeCount > 0 ? `${activeCount} run active` : "Idle"}
        </div>
      </div>
    </div>
  );
}