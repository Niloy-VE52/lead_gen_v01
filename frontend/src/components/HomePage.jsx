const IconActivity = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconCheck = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconLayers = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconPlay = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <path d="M3 2.5l10 5.5-10 5.5V2.5z" fill="currentColor"/>
  </svg>
);

const IconClock = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/>
    <path d="M12 7v5.5l3 2" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
  </svg>
);

const IconError = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8"/>
    <path d="M12 8v5M12 15.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

function StatCard({ icon, label, value, accent }) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ color: accent, background: `${accent}15` }}>
        {icon}
      </div>
      <div className="stat-body">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

function RecentRun({ run }) {
  const statusColor = {
    done: "var(--success)",
    error: "var(--danger)",
    unknown: "var(--text-faint)",
    running: "var(--accent)",
  }[run.status] || "var(--text-faint)";

  const date = run.timestamp
    ? new Date(run.timestamp).toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : "—";

  return (
    <div className="recent-run-item">
      <div className="recent-run-left">
        <span className="recent-run-dot" style={{ background: statusColor }} />
        <div>
          <div className="recent-run-id">#{run.run_id}</div>
          <div className="recent-run-step">{run.step}</div>
        </div>
      </div>
      <div className="recent-run-right">
        {run.jobs_added !== undefined && (
          <span className="recent-run-pill">{run.jobs_added} saved</span>
        )}
        {run.scored !== undefined && (
          <span className="recent-run-pill">{run.scored} scored</span>
        )}
        <span className="recent-run-date">
          <IconClock /> {date}
        </span>
      </div>
    </div>
  );
}

export default function HomePage({ runs, onNavigate, onLaunch, launching }) {
  const totalRuns    = runs.length;
  const totalSaved   = runs.reduce((s, r) => s + (r.jobs_added || 0), 0);
  const totalScored  = runs.reduce((s, r) => s + (r.scored || 0), 0);
  const errorCount   = runs.filter((r) => r.status === "error").length;
  const recentRuns   = [...runs].reverse().slice(0, 5);

  return (
    <div className="home-page">
      {/* Header */}
      <div className="home-header">
        <div>
          <h1 className="home-title">Overview</h1>
          <p className="home-subtitle">LeadGen Pipeline — Internal Operations</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="stats-grid">
        <StatCard icon={<IconActivity />} label="Total Runs"     value={totalRuns}   accent="#2563eb" />
        <StatCard icon={<IconLayers />}   label="Jobs Saved"     value={totalSaved}  accent="#059669" />
        <StatCard icon={<IconCheck />}    label="Jobs Scored"    value={totalScored} accent="#7c3aed" />
        <StatCard icon={<IconError />}    label="Failed Runs"    value={errorCount}  accent="#dc2626" />
      </div>

      {/* Two column: Quick Launch + Recent Runs */}
      <div className="home-cols">

        {/* Quick launch */}
        <div className="home-card">
          <div className="home-card-title">Quick Launch</div>
          <p className="home-card-desc">
            Start a full pipeline run with your saved configuration — scrape, enrich, score, and save to Google Sheets in one click.
          </p>
          <div className="home-pipeline-steps">
            {[
              "LinkedIn Scraper",
              "Repeatability Check",
              "Glassdoor Reviews",
              "Apollo Funding",
              "Lead Scoring",
              "Google Sheets Save",
            ].map((step, i) => (
              <div key={step} className="home-pipeline-step">
                <span className="home-step-num">{i + 1}</span>
                <span className="home-step-label">{step}</span>
                {i < 5 && <span className="home-step-arrow">→</span>}
              </div>
            ))}
          </div>
          <div className="home-card-actions">
            <button className="btn-launch" onClick={onLaunch} disabled={launching}>
              {launching
                ? <><div className="launch-spinner" /> Launching…</>
                : <><IconPlay /> Launch Full Pipeline</>}
            </button>
            <button className="btn-secondary" onClick={() => onNavigate("run")}>
              Configure
            </button>
          </div>
        </div>

        {/* Recent runs */}
        <div className="home-card">
          <div className="home-card-header">
            <div className="home-card-title">Recent Runs</div>
            {runs.length > 0 && (
              <button className="btn-link" onClick={() => onNavigate("history")}>
                View all →
              </button>
            )}
          </div>
          {recentRuns.length === 0 ? (
            <div className="home-empty">No runs yet. Launch your first pipeline above.</div>
          ) : (
            <div className="recent-runs-list">
              {recentRuns.map((r) => <RecentRun key={r.run_id} run={r} />)}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}