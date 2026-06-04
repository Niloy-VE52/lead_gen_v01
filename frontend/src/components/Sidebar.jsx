// SVG icons — no emojis
const IconRun = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M3 2.5l10 5.5-10 5.5V2.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
  </svg>
);

const IconHistory = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M8 5v3.5l2 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

export default function Sidebar({ tab, onTabChange, runCount, className = "" }) {
  return (
    <div className={`sidebar ${className}`}>
      <div className="sidebar-label">Navigation</div>
      <nav className="sidebar-nav">
        <div
          className={`nav-item ${tab === "run" ? "active" : ""}`}
          onClick={() => onTabChange("run")}
        >
          <IconRun />
          Run Pipeline
        </div>
        <div
          className={`nav-item ${tab === "history" ? "active" : ""}`}
          onClick={() => onTabChange("history")}
        >
          <IconHistory />
          Run History
          {runCount > 0 && (
            <span className="run-count-badge">{runCount}</span>
          )}
        </div>
      </nav>
    </div>
  );
}