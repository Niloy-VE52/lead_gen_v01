import { useState, useEffect, useCallback } from "react";
import { apiGet } from "../api/client";
import "./EmailOutreachTracker.css";

const IconRefresh = ({ spinning }) => (
  <svg
    width="14"
    height="14"
    viewBox="0 0 24 24"
    fill="none"
    style={{
      animation: spinning ? "spin 0.8s linear infinite" : "none",
      transition: "transform 0.2s ease",
    }}
  >
    <path
      d="M23 4v6h-6M1 20v-6h6"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

export default function EmailOutreachTracker() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [expandedRow, setExpandedRow] = useState(null);

  const fetchOutreach = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet("/outreach-status");
      if (res && res.entries) {
        setEntries(res.entries);
      }
    } catch (e) {
      console.warn("Could not fetch outreach status:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOutreach();
  }, [fetchOutreach]);

  // Derived metrics
  const total = entries.length;
  const liveSent = entries.filter((e) =>
    (e.outreachStatus || "").toUpperCase().includes("LIVE")
  ).length;
  const sandboxSent = entries.filter((e) =>
    (e.outreachStatus || "").toUpperCase().includes("SANDBOX")
  ).length;
  const pending = entries.filter((e) => {
    const s = (e.outreachStatus || "").toUpperCase();
    return s.includes("PENDING") || !s || s === "";
  }).length;
  const failed = entries.filter((e) =>
    (e.outreachStatus || "").toUpperCase().includes("FAIL")
  ).length;

  // Filtered entries
  const filtered = entries.filter((item) => {
    const status = (item.outreachStatus || "").toUpperCase();
    if (filter === "live" && !status.includes("LIVE")) return false;
    if (filter === "sandbox" && !status.includes("SANDBOX")) return false;
    if (filter === "pending" && !status.includes("PENDING") && status !== "") return false;
    if (filter === "failed" && !status.includes("FAIL")) return false;

    if (search.trim()) {
      const q = search.toLowerCase();
      const matchComp = (item.companyName || "").toLowerCase().includes(q);
      const matchName = (item.personName || "").toLowerCase().includes(q);
      const matchEmail = (item.email || "").toLowerCase().includes(q);
      const matchPipe = (item["pipeline ID"] || "").toLowerCase().includes(q);
      return matchComp || matchName || matchEmail || matchPipe;
    }
    return true;
  });

  const getBadgeClass = (statusStr) => {
    const s = (statusStr || "").toUpperCase();
    if (s.includes("LIVE")) return "live";
    if (s.includes("SANDBOX")) return "sandbox";
    if (s.includes("FAIL")) return "failed";
    return "pending";
  };

  return (
    <div className="outreach-tracker">
      <div className="tracker-header">
        <div className="tracker-title-area">
          <h2>✉️ Outreach History</h2>
          <p>
            Real-time delivery status of all outreach contacts and dispatched messages from{" "}
            <code>Email_saver</code>.
          </p>
        </div>
        <div className="tracker-header-actions">
          <button
            className="btn-refresh"
            onClick={fetchOutreach}
            disabled={loading}
            title="Refresh status from Google Sheet"
          >
            <IconRefresh spinning={loading} />
            {loading ? "Refreshing..." : "Refresh Status"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="tracker-stats-grid">
        <div className="tracker-stat-box">
          <span className="tracker-stat-val">{total}</span>
          <span className="tracker-stat-label">Total Leads</span>
        </div>
        <div className="tracker-stat-box">
          <span className="tracker-stat-val" style={{ color: "var(--success)" }}>
            {liveSent}
          </span>
          <span className="tracker-stat-label">Live Delivered</span>
        </div>
        <div className="tracker-stat-box">
          <span className="tracker-stat-val" style={{ color: "#2563eb" }}>
            {sandboxSent}
          </span>
          <span className="tracker-stat-label">Sandbox Tested</span>
        </div>
        <div className="tracker-stat-box">
          <span className="tracker-stat-val" style={{ color: "var(--warn)" }}>
            {pending}
          </span>
          <span className="tracker-stat-label">Pending Send</span>
        </div>
        <div className="tracker-stat-box">
          <span className="tracker-stat-val" style={{ color: "var(--danger)" }}>
            {failed}
          </span>
          <span className="tracker-stat-label">Delivery Failed</span>
        </div>
      </div>

      {/* Controls: Filter Pills & Search */}
      <div className="tracker-controls">
        <div className="tracker-filter-pills">
          <button
            className={`filter-pill ${filter === "all" ? "active" : ""}`}
            onClick={() => setFilter("all")}
          >
            All ({total})
          </button>
          <button
            className={`filter-pill ${filter === "live" ? "active" : ""}`}
            onClick={() => setFilter("live")}
          >
            Live Sent ({liveSent})
          </button>
          <button
            className={`filter-pill ${filter === "sandbox" ? "active" : ""}`}
            onClick={() => setFilter("sandbox")}
          >
            Sandbox ({sandboxSent})
          </button>
          <button
            className={`filter-pill ${filter === "pending" ? "active" : ""}`}
            onClick={() => setFilter("pending")}
          >
            Pending ({pending})
          </button>
          {failed > 0 && (
            <button
              className={`filter-pill ${filter === "failed" ? "active" : ""}`}
              onClick={() => setFilter("failed")}
            >
              Failed ({failed})
            </button>
          )}
        </div>

        <input
          type="text"
          className="tracker-search-input"
          placeholder="Search by company, name, email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table / List View */}
      {filtered.length === 0 ? (
        <div className="tracker-empty-state">
          <div className="tracker-empty-icon">📭</div>
          <div className="tracker-empty-text">
            {entries.length === 0
              ? "No contacts saved to Email_saver yet. When you run the pipeline on KEEP companies, their email delivery statuses will appear right here."
              : "No emails match your current filter or search query."}
          </div>
        </div>
      ) : (
        <div className="tracker-table-wrap">
          <table className="tracker-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Pipeline ID</th>
                <th>Company</th>
                <th>Decision Maker</th>
                <th>Recipient Email</th>
                <th>Sent / Added At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item, idx) => {
                const statusBadge = item.outreachStatus || "PENDING";
                const badgeClass = getBadgeClass(statusBadge);
                const isExpanded = expandedRow === idx;
                const timestamp = item.sentAt || item.addedAt || item["Date Time"] || "—";
                const pipelineId = item["pipeline ID"] || "—";

                return (
                  <>
                    <tr key={idx}>
                      <td>
                        <span className={`badge-status ${badgeClass}`}>
                          {badgeClass === "live" && "✓ "}
                          {badgeClass === "sandbox" && "🛡️ "}
                          {badgeClass === "pending" && "⏳ "}
                          {badgeClass === "failed" && "✕ "}
                          {statusBadge}
                        </span>
                      </td>
                      <td>
                        <span className="pipeline-tag">{pipelineId}</span>
                      </td>
                      <td>
                        <strong>{item.companyName || "—"}</strong>
                      </td>
                      <td>
                        <div>{item.personName || "—"}</div>
                        {item.designation && (
                          <div style={{ fontSize: "11px", color: "var(--text-faint)" }}>
                            {item.designation}
                          </div>
                        )}
                      </td>
                      <td>
                        <code style={{ fontSize: "12px", color: "var(--accent)" }}>
                          {item.email || "—"}
                        </code>
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-dim)", whiteSpace: "nowrap" }}>
                        {timestamp}
                      </td>
                      <td>
                        {(item.subject || item.emailBody) ? (
                          <button
                            className="btn-preview-toggle"
                            onClick={() => setExpandedRow(isExpanded ? null : idx)}
                          >
                            {isExpanded ? "Hide Email" : "View Email"}
                          </button>
                        ) : (
                          <span style={{ fontSize: "11px", color: "var(--text-faint)" }}>—</span>
                        )}
                      </td>
                    </tr>

                    {/* Expandable email body preview */}
                    {isExpanded && (
                      <tr className="email-preview-row">
                        <td colSpan={7}>
                          <div className="email-preview-content">
                            <div className="email-preview-subject">
                              <strong>Subject:</strong> {item.subject || "No subject recorded"}
                            </div>
                            <div className="email-preview-body">
                              {item.emailBody || "No email body recorded"}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
