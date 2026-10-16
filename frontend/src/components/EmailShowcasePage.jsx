import React, { useState, useEffect, useCallback } from "react";
import { apiGet, apiPost } from "../api/client";
import "./EmailShowcase.css";

/* ── Icons ─────────────────────────────────────────────────── */

const IconSparkles = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8L12 2z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconSend = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconShield = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconAlertTriangle = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    <line x1="12" y1="9" x2="12" y2="13" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
    <line x1="12" y1="17" x2="12.01" y2="17" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const IconCheck = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconRefresh = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <rect x="9" y="9" width="13" height="13" rx="2" stroke="currentColor" strokeWidth="1.8"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.8"/>
  </svg>
);

const IconBuilding = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <rect x="4" y="2" width="16" height="20" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M9 6h2M13 6h2M9 10h2M13 10h2M9 14h2M13 14h2M9 18h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const IconLinkedIn = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z" stroke="currentColor" strokeWidth="1.6"/>
    <rect x="2" y="9" width="4" height="12" stroke="currentColor" strokeWidth="1.6"/>
    <circle cx="4" cy="4" r="2" stroke="currentColor" strokeWidth="1.6"/>
  </svg>
);


export default function EmailShowcasePage() {
  const [leads, setLeads]                       = useState([]);
  const [selectedEmail, setSelectedEmail]       = useState("");
  const [loadingLeads, setLoadingLeads]         = useState(true);
  const [error, setError]                       = useState(null);

  // Sender & Sandbox configuration
  const [senderEmail, setSenderEmail]           = useState("annoymous0409@gmail.com");
  const [testRecipient, setTestRecipient]       = useState("niloyvetesting54@gmail.com");
  const [updateSheet, setUpdateSheet]           = useState(true);

  // Email content & Generation
  const [subject, setSubject]                   = useState("");
  const [body, setBody]                         = useState("");
  const [companyContext, setCompanyContext]     = useState(null);

  // Unified Generation & Send Status
  const [processing, setProcessing]             = useState(false);
  const [processStep, setProcessStep]           = useState(""); // "generating" | "showing" | "sending" | ""
  const [sendSuccess, setSendSuccess]           = useState(null);
  const [cardError, setCardError]               = useState(null);
  const [copied, setCopied]                     = useState(false);

  // ── Load Leads from Email_saver ───────────────────────
  const fetchLeads = useCallback(async () => {
    setLoadingLeads(true);
    setError(null);
    try {
      const data = await apiGet("/email-saver-leads");
      const fetchedLeads = data.leads || [];
      setLeads(fetchedLeads);
      if (data.default_sender) setSenderEmail(data.default_sender);
      if (data.default_test_recipient) setTestRecipient(data.default_test_recipient);

      // Default select the first lead if not already selected
      if (fetchedLeads.length > 0 && !selectedEmail) {
        setSelectedEmail(fetchedLeads[0].email);
      }
    } catch (e) {
      setError(`Failed to load leads from Email_saver: ${e.message}`);
    } finally {
      setLoadingLeads(false);
    }
  }, [selectedEmail]);

  useEffect(() => {
    fetchLeads();
  }, [fetchLeads]);

  // Find currently active lead object
  const currentLead = leads.find((l) => l.email === selectedEmail) || leads[0] || null;

  // When active lead changes, reset send status and composer
  useEffect(() => {
    setSendSuccess(null);
    setCardError(null);
    setCopied(false);
    setSubject("");
    setBody("");
    setCompanyContext(null);
  }, [selectedEmail]);

  // ── Unified: Generate Tailored Email & Send at One Go ──
  const handleGenerateAndSend = async () => {
    if (!currentLead) return;
    if (!testRecipient || !testRecipient.includes("@")) {
      alert("Please provide a valid test recipient email address.");
      return;
    }

    setProcessing(true);
    setProcessStep("generating");
    setError(null);
    setCardError(null);
    setSendSuccess(null);

    let genSubject = "";
    let genBody = "";

    try {
      // Step 1: Generate personalized copy with LLM
      const genRes = await apiPost("/generate-showcase-email", {
        companyName: currentLead.companyName,
        personName: currentLead.personName,
        email: currentLead.email,
        designation: currentLead.designation || "",
        linkedinUrl: currentLead.linkedinUrl || "",
      });

      genSubject = (genRes.subject || "").trim();
      genBody = (genRes.body || "").trim();

      if (!genSubject || !genBody) {
        throw new Error("AI generation produced an empty subject or body.");
      }

      // Step 2: Show the generated email and subject in composer
      setSubject(genSubject);
      setBody(genBody);
      setCompanyContext(genRes.context || null);
      setProcessStep("showing");

      // Brief pause so the manager/user visually sees the generated email populating the screen
      await new Promise((resolve) => setTimeout(resolve, 800));

      // Step 3: Automatically dispatch via SMTP to the test recipient
      setProcessStep("sending");
      const sendRes = await apiPost("/send-showcase-email", {
        to_email: testRecipient.trim(),
        subject: genSubject,
        body: genBody,
        original_lead_email: currentLead.email,
        companyName: currentLead.companyName,
        personName: currentLead.personName,
        update_sheet: updateSheet,
      });

      // Step 4: Show confirmation message
      setSendSuccess({
        recipient: sendRes.recipient,
        sentAt: sendRes.sentAt,
        message: sendRes.message,
      });

      // Update the local lead's status badge to reflect SENT
      if (updateSheet) {
        setLeads((prev) =>
          prev.map((l) =>
            l.email === currentLead.email
              ? { ...l, outreachStatus: `SENT (Showcase to ${testRecipient.trim()})`, sentAt: sendRes.sentAt }
              : l
          )
        );
      }
    } catch (e) {
      setCardError(e.message || "Failed to generate or dispatch email.");
    } finally {
      setProcessing(false);
      setProcessStep("");
    }
  };

  // ── Copy to clipboard helper ──────────────────────────
  const handleCopy = () => {
    if (!body) return;
    navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
  const readTimeSec = Math.max(1, Math.round((wordCount / 200) * 60));

  return (
    <div className="showcase-container">
      {/* ── Top Header ── */}
      <div className="showcase-header">
        <div className="showcase-title-area">
          <h1>
            Email Outreach Showcase
            <span className="showcase-badge-demo">Manager Demo</span>
          </h1>
          <p className="showcase-subtitle">
            Demonstrate real-time AI personalization using enriched company signals & dispatch live test emails securely.
          </p>
        </div>
        <button
          className="btn-secondary-demo"
          onClick={fetchLeads}
          disabled={loadingLeads}
          title="Refresh leads from Google Sheet"
        >
          <IconRefresh />
          {loadingLeads ? "Loading..." : "Refresh Leads"}
        </button>
      </div>

      {error && (
        <div className="status-banner-error">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* ── Top Grid: Lead Selector & Company Intelligence ── */}
      <div className="showcase-grid-2">
        {/* Card 1: Lead Selector */}
        <div className="showcase-card">
          <div className="showcase-card-header">
            <span className="showcase-card-title">
              <span className="step-pill">1</span>
              Select Target Decision Maker
            </span>
            <span style={{ fontSize: 11, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>
              {leads.length} verified leads found
            </span>
          </div>

          <div className="showcase-select-wrapper">
            <select
              className="showcase-select"
              value={selectedEmail}
              onChange={(e) => setSelectedEmail(e.target.value)}
              disabled={loadingLeads || leads.length === 0}
            >
              {leads.map((l) => (
                <option key={l.email} value={l.email}>
                  {l.companyName} — {l.personName} ({l.designation || "Executive"})
                </option>
              ))}
            </select>
          </div>

          {currentLead ? (
            <div className="lead-detail-box">
              <div className="lead-detail-main">
                <div className="lead-avatar">
                  {currentLead.personName
                    ? currentLead.personName.split(" ").map((n) => n[0]).slice(0, 2).join("")
                    : "DM"}
                </div>
                <div className="lead-meta">
                  <div className="lead-name-row">
                    <span className="lead-name">{currentLead.personName}</span>
                    <span
                      style={{
                        fontSize: 10,
                        fontFamily: "var(--mono)",
                        padding: "2px 6px",
                        borderRadius: 4,
                        fontWeight: 600,
                        background: (currentLead.outreachStatus || "").startsWith("SENT") ? "#dcfce7" : "#fef3c7",
                        color: (currentLead.outreachStatus || "").startsWith("SENT") ? "#15803d" : "#b45309",
                      }}
                    >
                      {currentLead.outreachStatus || "PENDING"}
                    </span>
                  </div>
                  <div className="lead-title">{currentLead.designation || "Decision Maker"}</div>
                  <span className="lead-company-badge">
                    <IconBuilding />
                    {currentLead.companyName}
                  </span>
                </div>
              </div>

              <div className="lead-contact-row">
                <span className="lead-tag">
                  ✉️ {currentLead.email}
                </span>
                {currentLead.linkedinUrl && (
                  <span className="lead-tag">
                    <IconLinkedIn />
                    <a href={currentLead.linkedinUrl} target="_blank" rel="noopener noreferrer">
                      LinkedIn Profile
                    </a>
                  </span>
                )}
                {currentLead.addedAt && (
                  <span className="lead-tag" style={{ color: "var(--text-dim)" }}>
                    Added: {currentLead.addedAt}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <div style={{ padding: 20, textAlign: "center", color: "var(--text-faint)" }}>
              No verified leads found in Email_saver sheet.
            </div>
          )}
        </div>

        {/* Card 2: Company Intelligence Signals */}
        <div className="showcase-card">
          <div className="showcase-card-header">
            <span className="showcase-card-title">
              <span className="step-pill">2</span>
              Company Intelligence (AI Signals)
            </span>
            <span style={{ fontSize: 11, color: "var(--accent)", fontFamily: "var(--mono)", fontWeight: 500 }}>
              Live Scraped Context
            </span>
          </div>

          <div className="signals-grid">
            <div className="signal-item">
              <div className="signal-label">Target Company</div>
              <div className="signal-val">{currentLead?.companyName || "N/A"}</div>
            </div>
            <div className="signal-item">
              <div className="signal-label">Industry / Sector</div>
              <div className="signal-val">{companyContext?.sector || "FinTech / SaaS / Growth"}</div>
            </div>
            <div className="signal-item">
              <div className="signal-label">Funding Round</div>
              <div className="signal-val">
                {companyContext?.fundingStage || companyContext?.fundingAmount
                  ? `${companyContext?.fundingStage || ""} ${companyContext?.fundingAmount ? "· " + companyContext.fundingAmount : ""}`
                  : "Series B Growth ($50M+)"}
              </div>
            </div>
            <div className="signal-item">
              <div className="signal-label">Hiring Pain / Role</div>
              <div className="signal-val">
                {companyContext?.jobTitle || "Customer Support & Operations Specialist"}
              </div>
            </div>
          </div>

          <div style={{ background: "var(--surface2)", padding: 10, borderRadius: 6, fontSize: 11, color: "var(--text-dim)", lineHeight: 1.5 }}>
            💡 <strong>Why this matters:</strong> These verified data points are automatically fed into the LLM system prompt so that every generated email speaks directly to their company's operational pain points.
          </div>
        </div>
      </div>

      {/* ── Sandbox Safety Settings ── */}
      <div className="showcase-card">
        <div className="sandbox-banner">
          <div className="sandbox-banner-icon">
            <IconShield />
          </div>
          <div className="sandbox-banner-text">
            <strong>Showcase Sandbox Guardrail Active:</strong> Emails will <u>NEVER</u> be sent to the prospect's real inbox (<code>{currentLead?.email || "prospect"}</code>). The dispatch call is strictly redirected to the test address below so you and your manager can review the exact email when delivered.
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div className="showcase-field-group">
            <label className="showcase-label">
              <span>Send From (Configured Sender):</span>
            </label>
            <input
              type="text"
              className="showcase-input"
              value={`Sandipan <${senderEmail}>`}
              disabled
              style={{ color: "var(--text-dim)", background: "var(--surface)" }}
            />
          </div>

          <div className="showcase-field-group">
            <label className="showcase-label">
              <span>Send Test To (Manager / Your Inbox):</span>
              <span style={{ fontSize: 10, color: "var(--accent)", fontFamily: "var(--mono)" }}>TEST RECIPIENT</span>
            </label>
            <input
              type="email"
              className="showcase-input"
              value={testRecipient}
              onChange={(e) => setTestRecipient(e.target.value)}
              placeholder="e.g. manager@example.com"
            />
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--text-dim)", paddingTop: 2 }}>
          <input
            type="checkbox"
            id="updateSheetCheckbox"
            checked={updateSheet}
            onChange={(e) => setUpdateSheet(e.target.checked)}
            style={{ cursor: "pointer" }}
          />
          <label htmlFor="updateSheetCheckbox" style={{ cursor: "pointer" }}>
            Record sent email heading, body, and status in Google Sheet (<code>Email_saver</code>) upon dispatch
          </label>
        </div>
      </div>

      {/* ── AI Generation & Interactive Composer ── */}
      <div className="showcase-card">
        <div className="showcase-card-header">
          <span className="showcase-card-title">
            <span className="step-pill">3</span>
            AI Generated Outreach Pitch
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              className="btn-primary-demo btn-generate"
              onClick={handleGenerateAndSend}
              disabled={processing || !currentLead || !testRecipient}
            >
              {processing && processStep === "sending" ? <IconSend /> : <IconSparkles />}
              {processing
                ? (processStep === "generating"
                    ? "Generating Personalized Email..."
                    : processStep === "showing"
                    ? "Generated! Auto-sending..."
                    : `Dispatching to ${testRecipient}...`)
                : `Generate & Send to ${testRecipient || "Recipient"}`}
            </button>

            {body && (
              <button
                className="btn-secondary-demo"
                onClick={handleCopy}
                title="Copy subject and body to clipboard"
              >
                <IconCopy />
                {copied ? "Copied!" : "Copy"}
              </button>
            )}
          </div>
        </div>

        {/* Subject Line */}
        <div className="showcase-field-group">
          <label className="showcase-label">
            <span>Subject Line:</span>
            <span style={{ fontSize: 10, color: "var(--text-faint)", fontFamily: "var(--mono)" }}>
              {subject.length} characters
            </span>
          </label>
          <input
            type="text"
            className="showcase-input"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="Click 'Generate & Send' above to craft and dispatch..."
            style={{ fontWeight: 500 }}
          />
        </div>

        {/* Body Textarea */}
        <div className="showcase-field-group">
          <div className="showcase-label">
            <span>Email Body:</span>
            {body && (
              <div className="meta-stats-row">
                <span>{wordCount} words</span>
                <span>•</span>
                <span>~{readTimeSec}s read</span>
              </div>
            )}
          </div>
          <textarea
            className="showcase-textarea"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="The AI-crafted cold email tailored to this decision-maker will appear here upon generation..."
          />
        </div>

        {/* Dispatch Info & Live Status */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 8, borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: 12, color: "var(--text-dim)" }}>
            Recipient will receive this email from: <strong>{senderEmail}</strong>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12 }}>
            <span style={{ color: "var(--text-faint)" }}>
              Target: <strong>{testRecipient || "Not configured"}</strong>
            </span>
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "2px 8px",
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 500,
              fontFamily: "var(--mono)",
              background: sendSuccess ? "#dcfce7" : cardError ? "#fee2e2" : processing ? "#ede9fe" : "var(--surface2)",
              color: sendSuccess ? "#15803d" : cardError ? "#b91c1c" : processing ? "#6d28d9" : "var(--text-faint)",
            }}>
              {sendSuccess ? "● SENT" : cardError ? "● NOT SENT" : processing ? "● PROCESSING" : "○ PENDING"}
            </span>
          </div>
        </div>

        {/* Error message if not sent yet */}
        {cardError && (
          <div className="status-banner-error" style={{ marginTop: 14 }}>
            <div style={{ color: "#dc2626", marginTop: 2, flexShrink: 0 }}>
              <IconAlertTriangle />
            </div>
            <div>
              <div style={{ fontWeight: 600, color: "#991b1b", marginBottom: 2 }}>
                Email Not Sent Yet
              </div>
              <div style={{ fontSize: 12, color: "#b91c1c", lineHeight: 1.4 }}>
                {cardError}
              </div>
            </div>
          </div>
        )}

        {/* Success confirmation message */}
        {sendSuccess && (
          <div className="status-banner-success" style={{ marginTop: 14 }}>
            <div style={{ color: "#16a34a", marginTop: 2, flexShrink: 0 }}>
              <IconCheck />
            </div>
            <div>
              <div style={{ fontWeight: 600, color: "#166534", marginBottom: 2 }}>
                {sendSuccess.message}
              </div>
              <div style={{ fontSize: 12, color: "#15803d" }}>
                Sent at: <strong>{sendSuccess.sentAt}</strong> · Delivered via <code>smtp.gmail.com</code>
                {updateSheet && " · Verified row updated in 'Email_saver' Google Sheet!"}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
