import ConfigPanel from "./ConfigPanel";
import RunMonitor from "./RunMonitor";

const IconInfo = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="none" className="info-box-icon">
    <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M8 7.5v4M8 5.5v.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconRadar = () => (
  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
    <circle cx="16" cy="16" r="13" stroke="#d0d5dd" strokeWidth="1.5"/>
    <circle cx="16" cy="16" r="8" stroke="#d0d5dd" strokeWidth="1.5"/>
    <circle cx="16" cy="16" r="3" stroke="#d0d5dd" strokeWidth="1.5"/>
    <path d="M16 16L24 8" stroke="#d0d5dd" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
);

const IconPlay = () => (
  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
    <path d="M3 2.5l10 5.5-10 5.5V2.5z" fill="currentColor"/>
  </svg>
);

export default function RunPage({
  config, onConfigChange, onLaunch, launching, error, activeRunId, onRunDone,
}) {
  return (
    <>
      <div className="section-heading">Pipeline Configuration</div>

      <div className="info-box">
        <IconInfo />
        <div>
          <p>
            Runs the <strong style={{ color: "var(--text)" }}>full end-to-end pipeline</strong>:
            Scrape LinkedIn → Repeatability → Reviews → Funding → Score → Save to Google Sheets.
          </p>
          <p>
            Results are written to <code>Scaped_v6</code> and <code>Score_Listing_v6</code>.
          </p>
        </div>
      </div>

      <ConfigPanel config={config} onChange={onConfigChange} />

      <div className="launch-row">
        <button className="btn-launch" onClick={onLaunch} disabled={launching}>
          {launching ? (
            <><div className="launch-spinner" /> Launching…</>
          ) : (
            <><IconPlay /> Launch Full Pipeline</>
          )}
        </button>
        {error && <div className="error-msg">Error: {error}</div>}
      </div>

      <div className="section-heading">Live Monitor</div>

      {activeRunId ? (
        <RunMonitor runId={activeRunId} onDone={onRunDone} />
      ) : (
        <div className="empty-monitor">
          <div className="empty-monitor-icon"><IconRadar /></div>
          <div className="empty-monitor-text">No active run. Launch the pipeline above to begin.</div>
        </div>
      )}
    </>
  );
}