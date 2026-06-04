import StatusBadge from "./StatusBadge";

export default function RunHistory({ runs, activeRunId }) {
  if (runs.length === 0) {
    return (
      <div className="history-empty">No pipeline runs yet this session.</div>
    );
  }

  return (
    <div className="history-list">
      {[...runs].reverse().map((r) => (
        <div
          key={r.run_id}
          className={`history-item ${r.run_id === activeRunId ? "history-active" : ""}`}
        >
          <div className="history-top">
            <span className="history-id">#{r.run_id}</span>
            <StatusBadge status={r.status} />
          </div>
          <div className="history-step">{r.step}</div>
          <div className="history-meta">
            {r.jobs_added !== undefined && <span>Saved: {r.jobs_added}</span>}
            {r.scored !== undefined && <span>Scored: {r.scored}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
