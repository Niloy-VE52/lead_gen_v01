const IconHome = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none">
    <path d="M2 6.5L8 2l6 4.5V14H10v-3.5H6V14H2V6.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
  </svg>
);
const IconRun = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none">
    <path d="M3 2.5l10 5.5-10 5.5V2.5z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
  </svg>
);
const IconHistory = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none">
    <circle cx="8" cy="8" r="5.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M8 5v3.5l2 1.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);
const IconSheet = () => (
  <svg className="nav-icon" viewBox="0 0 16 16" fill="none">
    <rect x="2" y="2" width="12" height="12" rx="1.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M2 6h12M2 10h12M6 2v12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const NAV_ITEMS = [
  { id: "home",    label: "Home",         Icon: IconHome    },
  { id: "run",     label: "Run Pipeline", Icon: IconRun     },
  { id: "history", label: "Run History",  Icon: IconHistory },
  { id: "sheets",  label: "Sheets",       Icon: IconSheet   },
];

export default function Sidebar({ tab, onTabChange, runCount, className = "" }) {
  return (
    <div className={`sidebar ${className}`}>
      <div className="sidebar-label">Navigation</div>
      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ id, label, Icon }) => (
          <div
            key={id}
            className={`nav-item ${tab === id ? "active" : ""}`}
            onClick={() => onTabChange(id)}
          >
            <Icon />
            {label}
            {id === "history" && runCount > 0 && (
              <span className="run-count-badge">{runCount}</span>
            )}
          </div>
        ))}
      </nav>
    </div>
  );
}