import { useState, useEffect, useCallback, useMemo } from "react";
import { apiGet, apiPost } from "../api/client";
import "./ManualOutreach.css";

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

const IconSend = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path
      d="M22 2L11 13"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M22 2L15 22L11 13L2 9L22 2Z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

const isFailedStatus = (statusStr) => {
  const s = (statusStr || "").toUpperCase();
  return (
    (s.includes("FAIL") || s.includes("ERROR") || (s.includes("PENDING") && !s.includes("SENT"))) &&
    !s.includes("MANUAL")
  );
};

export default function ManualOutreach({ onNavigate }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedCompany, setSelectedCompany] = useState("");
  const [selectedLeadIdx, setSelectedLeadIdx] = useState(0);

  // Form states
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [recipientEmail, setRecipientEmail] = useState("");
  const [outreachMode, setOutreachMode] = useState("test");
  const [testEmailRecipient, setTestEmailRecipient] = useState("niloyvetesting54@gmail.com");

  // Send action state
  const [sending, setSending] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const fetchOutreach = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiGet("/outreach-status");
      if (res && res.entries) {
        setEntries(res.entries);
      }
    } catch (e) {
      console.warn("Could not fetch outreach records:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOutreach();
  }, [fetchOutreach]);

  // Group failed leads by company
  const companyFailedMap = useMemo(() => {
    const map = {};
    entries.forEach((e) => {
      if (isFailedStatus(e.outreachStatus)) {
        const comp = (e.companyName || "Unknown Company").trim();
        if (!map[comp]) map[comp] = [];
        map[comp].push(e);
      }
    });
    return map;
  }, [entries]);

  const failedCompanies = useMemo(() => Object.keys(companyFailedMap).sort(), [companyFailedMap]);

  // If currently selected company is no longer in failed companies list, reset
  useEffect(() => {
    if (selectedCompany && !companyFailedMap[selectedCompany]) {
      setSelectedCompany(failedCompanies[0] || "");
      setSelectedLeadIdx(0);
    } else if (!selectedCompany && failedCompanies.length > 0) {
      setSelectedCompany(failedCompanies[0]);
      setSelectedLeadIdx(0);
    }
  }, [failedCompanies, companyFailedMap, selectedCompany]);

  // Get active leads for the selected company
  const currentCompanyLeads = useMemo(() => {
    return selectedCompany && companyFailedMap[selectedCompany] ? companyFailedMap[selectedCompany] : [];
  }, [selectedCompany, companyFailedMap]);

  // Active lead
  const currentLead = currentCompanyLeads[selectedLeadIdx] || currentCompanyLeads[0] || null;

  // Whenever currentLead changes, sync fields
  useEffect(() => {
    if (currentLead) {
      setSubject(currentLead.subject || "");
      setBody(currentLead.emailBody || "");
      setRecipientEmail(currentLead.email || "");
      setFeedback(null);
    } else {
      setSubject("");
      setBody("");
      setRecipientEmail("");
    }
  }, [currentLead]);

  const handleSend = async () => {
    if (!currentLead) return;
    setSending(true);
    setFeedback(null);

    const actualRecipient = outreachMode === "live" ? recipientEmail : testEmailRecipient;
    if (!actualRecipient || !actualRecipient.includes("@")) {
      setFeedback({
        type: "error",
        message: `Please specify a valid email address for delivery (${outreachMode === "live" ? "Recipient Email" : "Test Email"}).`,
      });
      setSending(false);
      return;
    }

    try {
      const payload = {
        email: currentLead.email || recipientEmail,
        company_name: currentLead.companyName || selectedCompany,
        person_name: currentLead.personName || "Prospect",
        subject: subject,
        body: body,
        outreach_mode: outreachMode,
        test_email_recipient: testEmailRecipient,
      };

      const res = await apiPost("/manual-send", payload);

      if (res && res.success) {
        setFeedback({
          type: "success",
          message: `Email successfully sent to ${res.recipient}! Status updated in Google Sheet and Outreach History as: "${res.status}".`,
        });

        // Update the entry locally so it immediately shows as manually sent
        setEntries((prev) =>
          prev.map((e) => {
            const matchEmail = (e.email || "").trim().toLowerCase() === (currentLead.email || "").trim().toLowerCase();
            const matchName =
              (e.personName || "").trim().toLowerCase() === (currentLead.personName || "").trim().toLowerCase() &&
              (e.companyName || "").trim().toLowerCase() === (currentLead.companyName || "").trim().toLowerCase();

            if (matchEmail || matchName) {
              return {
                ...e,
                outreachStatus: res.status,
                sentAt: res.sent_at,
                subject: subject,
                emailBody: body,
              };
            }
            return e;
          })
        );
      } else {
        setFeedback({
          type: "error",
          message: res?.error || "Failed to deliver manual outreach email. Please verify SMTP credentials.",
        });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "An error occurred while dispatching manual email.",
      });
    } finally {
      setSending(false);
    }
  };

  const handleRegenerate = async () => {
    if (!currentLead) return;
    setRegenerating(true);
    setFeedback(null);
    try {
      const payload = {
        company_name: currentLead.companyName || selectedCompany,
        person_name: currentLead.personName || "Prospect",
        designation: currentLead.designation || "",
        email: currentLead.email || recipientEmail,
      };

      const res = await apiPost("/regenerate-email", payload);
      if (res && res.success) {
        setSubject(res.subject || subject);
        setBody(res.body || body);
        setFeedback({
          type: "success",
          message: "Email copy successfully re-generated using the latest active template!",
        });
      } else {
        setFeedback({
          type: "error",
          message: res?.error || "Failed to regenerate email copy.",
        });
      }
    } catch (err) {
      setFeedback({
        type: "error",
        message: err.message || "An error occurred while regenerating email copy.",
      });
    } finally {
      setRegenerating(false);
    }
  };

  return (
    <div className="manual-outreach-container">
      {/* Header */}
      <div className="manual-header">
        <div className="manual-title-area">
          <h2>✍️ Manual Outreach Dispatcher</h2>
          <p className="manual-subtitle">
            Review, edit, and manually send generated emails that failed during automated pipeline runs.
            Delivering here automatically updates the <strong>Outreach History</strong> and Google Sheets with a
            <strong> Manually Sent</strong> status.
          </p>
        </div>
        <div className="manual-header-actions">
          <button
            className="btn-refresh"
            onClick={fetchOutreach}
            disabled={loading}
            title="Refresh failed emails from Google Sheets"
          >
            <IconRefresh spinning={loading} />
            {loading ? "Checking..." : "Refresh Status"}
          </button>
        </div>
      </div>

      {/* No Failed Emails State */}
      {failedCompanies.length === 0 ? (
        <div className="manual-all-clear">
          <div className="all-clear-icon">🎉</div>
          <h3>All Outreach Emails Delivered!</h3>
          <p>
            No failed emails found in <code>Email_saver</code>. All generated outreach messages have been
            successfully delivered.
          </p>
          {onNavigate && (
            <button className="btn-secondary" onClick={() => onNavigate("outreach")}>
              View Outreach History
            </button>
          )}
        </div>
      ) : (
        <div className="manual-content-grid">
          {/* Left Column: Company & Lead Selection */}
          <div className="manual-sidebar-panel">
            <div className="panel-section">
              <label className="section-label">1. Select Company with Failed Outreach</label>
              <div className="custom-select-wrapper">
                <select
                  className="company-select-dropdown"
                  value={selectedCompany}
                  onChange={(e) => {
                    setSelectedCompany(e.target.value);
                    setSelectedLeadIdx(0);
                  }}
                >
                  {failedCompanies.map((comp) => {
                    const count = companyFailedMap[comp].length;
                    return (
                      <option key={comp} value={comp}>
                        🏢 {comp} ({count} failed {count === 1 ? "lead" : "leads"})
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>

            {/* Decision Makers List for Selected Company */}
            {currentCompanyLeads.length > 0 && (
              <div className="panel-section">
                <label className="section-label">
                  2. Select Decision Maker ({currentCompanyLeads.length})
                </label>
                <div className="leads-selector-list">
                  {currentCompanyLeads.map((lead, idx) => {
                    const isSelected = idx === selectedLeadIdx;
                    return (
                      <div
                        key={idx}
                        className={`lead-card-item ${isSelected ? "active" : ""}`}
                        onClick={() => setSelectedLeadIdx(idx)}
                      >
                        <div className="lead-card-top">
                          <span className="lead-card-name">{lead.personName || "Unnamed Lead"}</span>
                          <span className="lead-failed-badge">Failed</span>
                        </div>
                        {lead.designation && <div className="lead-card-title">{lead.designation}</div>}
                        <div className="lead-card-email">{lead.email || "No email"}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Email Editor & Dispatcher */}
          <div className="manual-composer-panel">
            {currentLead ? (
              <div className="composer-card">
                <div className="composer-header">
                  <div className="composer-lead-info">
                    <span className="composer-company-badge">{currentLead.companyName}</span>
                    <h3>{currentLead.personName}</h3>
                    <span className="composer-designation">{currentLead.designation || "Decision Maker"}</span>
                  </div>
                  <div className="failure-reason-box">
                    <span className="failure-label">Previous Error:</span>
                    <span className="failure-text">{currentLead.outreachStatus || "Delivery Failed"}</span>
                  </div>
                </div>

                {/* Feedback Notification */}
                {feedback && (
                  <div className={`manual-feedback-banner ${feedback.type}`}>
                    <div className="feedback-content">
                      <span>{feedback.type === "success" ? "✅" : "⚠️"}</span>
                      <span>{feedback.message}</span>
                    </div>
                    {feedback.type === "success" && onNavigate && (
                      <button className="btn-link" onClick={() => onNavigate("outreach")}>
                        Go to Outreach History →
                      </button>
                    )}
                  </div>
                )}

                {/* Delivery Mode Toggle */}
                <div className="delivery-mode-section">
                  <label className="section-label">Outreach Delivery Mode</label>
                  <div className="delivery-mode-pills">
                    <button
                      type="button"
                      className={`mode-pill ${outreachMode === "test" ? "active sandbox" : ""}`}
                      onClick={() => setOutreachMode("test")}
                    >
                      🛡️ Test Sandbox (Safe Route)
                    </button>
                    <button
                      type="button"
                      className={`mode-pill ${outreachMode === "live" ? "active live" : ""}`}
                      onClick={() => setOutreachMode("live")}
                    >
                      🔥 Live Prospect Delivery
                    </button>
                  </div>

                  {outreachMode === "test" ? (
                    <div className="mode-explainer sandbox">
                      <span>Delivering safely to test inbox:</span>
                      <input
                        type="email"
                        className="mode-email-input"
                        value={testEmailRecipient}
                        onChange={(e) => setTestEmailRecipient(e.target.value)}
                        placeholder="test@example.com"
                      />
                    </div>
                  ) : (
                    <div className="mode-explainer live">
                      <span>Will deliver directly to prospect address:</span>
                      <code>{recipientEmail || currentLead.email}</code>
                    </div>
                  )}
                </div>

                {/* Form Inputs */}
                <div className="form-group">
                  <label className="input-label">Recipient Prospect Email</label>
                  <input
                    type="email"
                    className="manual-input"
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    placeholder="prospect@company.com"
                  />
                </div>

                <div className="form-group">
                  <label className="input-label">Subject Line</label>
                  <input
                    type="text"
                    className="manual-input"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="Enter email subject line..."
                  />
                </div>

                <div className="form-group">
                  <div className="textarea-label-row">
                    <label className="input-label">
                      Email Body Content (Personalized & Ready to Dispatch)
                    </label>
                    <button
                      type="button"
                      className="btn-regenerate"
                      onClick={handleRegenerate}
                      disabled={regenerating || sending}
                      title="Re-generate this email using the latest saved template"
                    >
                      <IconRefresh spinning={regenerating} />
                      {regenerating ? "Regenerating Copy..." : "✨ Regenerate with Current Template"}
                    </button>
                  </div>
                  <textarea
                    className="manual-textarea"
                    rows={14}
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    placeholder="Enter email body..."
                  />
                </div>

                {/* Submit Actions */}
                <div className="composer-actions">
                  <button
                    className="btn-primary-send"
                    onClick={handleSend}
                    disabled={sending || regenerating || !subject.trim() || !body.trim()}
                  >
                    <IconSend />
                    {sending
                      ? "Dispatching Email..."
                      : outreachMode === "live"
                      ? "Send Live Email Now"
                      : "Send Test Email Now"}
                  </button>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={handleRegenerate}
                    disabled={regenerating || sending}
                    title="Regenerate this email using the latest saved template"
                  >
                    <IconRefresh spinning={regenerating} />
                    {regenerating ? "Regenerating..." : "Regenerate Template"}
                  </button>
                  {onNavigate && (
                    <button
                      type="button"
                      className="btn-secondary"
                      onClick={() => onNavigate("outreach")}
                    >
                      View in Outreach History
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="composer-placeholder">
                <p>Select a failed company and contact from the left panel to review and dispatch.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
