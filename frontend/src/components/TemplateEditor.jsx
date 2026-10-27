import { useState, useEffect, useCallback } from "react";
import { apiGet, apiPost } from "../api/client";
import "./TemplateEditor.css";

const DEFAULT_FALLBACK = {
  sender_name: "Sandipan Sarkar",
  sender_title: "Outsourcing & Operations",
  sender_company: "Virtual Employee",
  subject_instruction: "3 to 6 words maximum. Lowercase or sentence case. No spam words (e.g. Scaling support at {company_name}).",
  value_proposition: "We provide dedicated, pre-vetted remote talent and support specialists tailored specifically to fast-growing companies, eliminating slow hiring bottlenecks, recruitment fees, and overhead of full-time staffing.",
  closing_body: `Free Trial and Candidate Selection
To help you make an informed decision, we would be happy to offer a free trial with a suitable in-house professional. This will allow you to evaluate their technical expertise, communication, collaboration, and overall fit with your team before making any commitment.

You can also explore our Virtual Employee Candidate Trial Portal (https://trials.virtualemployee.com/v2?utm_source=api&utm_medium=automation&utm_campaign=api_automation) to:
• Browse available candidates and filter them by domain and skill set.
• Review candidate profiles and resumes.
• Select the professional who best matches your requirements.
• Start a free trial and evaluate the engagement firsthand.

If you're open to exploring this option, I'd be happy to arrange a short call to understand your support requirements or share a few relevant candidate profiles for your review.

We look forward to the opportunity to support {company_name} in finding the right talent and building a scalable, cost-effective support team.

Best regards,
{sender_name}
{sender_title} | {sender_company}`,
  last_updated: ""
};

export default function TemplateEditor() {
  const [template, setTemplate] = useState(() => {
    try {
      const cached = localStorage.getItem("lead_gen_template");
      return cached ? JSON.parse(cached) : DEFAULT_FALLBACK;
    } catch {
      return DEFAULT_FALLBACK;
    }
  });

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState(null);

  // Fetch from backend
  const fetchTemplate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet("/email-template");
      if (data && data.closing_body) {
        setTemplate(data);
        localStorage.setItem("lead_gen_template", JSON.stringify(data));
      }
    } catch (err) {
      console.warn("Could not fetch template from backend, using local copy:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTemplate();
  }, [fetchTemplate]);

  const handleChange = (field, value) => {
    setTemplate((prev) => ({ ...prev, [field]: value }));
    setSaveSuccess(false);
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSaveSuccess(false);
    try {
      const res = await apiPost("/email-template", template);
      if (res && res.template) {
        setTemplate(res.template);
        localStorage.setItem("lead_gen_template", JSON.stringify(res.template));
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 4000);
      }
    } catch (err) {
      setError(err.message || "Failed to save template to server.");
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm("Reset this email template back to the original default? Any unsaved edits will be lost.")) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await apiPost("/email-template/reset", {});
      if (res && res.template) {
        setTemplate(res.template);
        localStorage.setItem("lead_gen_template", JSON.stringify(res.template));
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 4000);
      }
    } catch (err) {
      setError(err.message || "Failed to reset template.");
    } finally {
      setSaving(false);
    }
  };

  const insertTag = (tag) => {
    setTemplate((prev) => ({
      ...prev,
      closing_body: prev.closing_body + " " + tag
    }));
  };

  // Generate simulated preview
  const previewCompany = "Acme Global";
  const previewClosing = (template.closing_body || "")
    .replace(/{company_name}/g, previewCompany)
    .replace(/{comp}/g, previewCompany)
    .replace(/{sender_name}/g, template.sender_name || "Sandipan Sarkar")
    .replace(/{sender_title}/g, template.sender_title || "Outsourcing & Operations")
    .replace(/{sender_company}/g, template.sender_company || "Virtual Employee");

  const renderFormattedPreview = (text) => {
    if (!text) return null;
    const regex = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
    const elements = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        elements.push(text.substring(lastIndex, match.index));
      }
      elements.push(
        <a
          key={match.index}
          href={match[2]}
          target="_blank"
          rel="noreferrer"
          style={{ color: "#2563eb", textDecoration: "underline", fontWeight: 600 }}
        >
          {match[1]}
        </a>
      );
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      elements.push(text.substring(lastIndex));
    }

    return (
      <span style={{ whiteSpace: "pre-wrap" }}>
        {elements}
      </span>
    );
  };

  return (
    <div className="template-editor-container">
      {/* Top Header */}
      <div className="template-header">
        <div>
          <h2>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9"/>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>
            </svg>
            Outreach Email Template
          </h2>
          <p className="template-subtitle">
            View, customize, and save the email template used by the pipeline to contact decision makers. Changes are permanently saved for all future runs.
          </p>
        </div>

        <div className="template-actions">
          {saveSuccess && (
            <span className="save-success-pill">
              ✓ Template Saved!
            </span>
          )}
          <button className="btn-secondary" onClick={handleReset} disabled={saving || loading}>
            ↺ Reset to Default
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={saving || loading}>
            {saving ? "Saving..." : "💾 Save Template"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: "#fee2e2", border: "1px solid #f87171", color: "#991b1b", padding: "12px 16px", borderRadius: "8px", fontSize: "13px" }}>
          {error}
        </div>
      )}

      {/* Main Grid: Editor on Left, Live Preview on Right */}
      <div className="template-grid">
        {/* Editor Column */}
        <div className="card">
          <h3 className="card-title">
            <span>✏️</span> Edit Template Details
          </h3>
          <p className="card-desc">
            Edit the parameters below. When saved, the AI copywriter will automatically use this exact layout.
          </p>

          {/* Sender Identity */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            <div className="form-group">
              <label>Sender Name</label>
              <input
                className="form-input"
                type="text"
                value={template.sender_name || ""}
                onChange={(e) => handleChange("sender_name", e.target.value)}
                placeholder="e.g. Sandipan Sarkar"
              />
            </div>
            <div className="form-group">
              <label>Sender Title</label>
              <input
                className="form-input"
                type="text"
                value={template.sender_title || ""}
                onChange={(e) => handleChange("sender_title", e.target.value)}
                placeholder="e.g. Outsourcing & Operations"
              />
            </div>
          </div>

          <div className="form-group">
            <label>Sender Company</label>
            <input
              className="form-input"
              type="text"
              value={template.sender_company || ""}
              onChange={(e) => handleChange("sender_company", e.target.value)}
              placeholder="e.g. Virtual Employee"
            />
          </div>

          {/* AI Prompt */}
          <div className="form-group">
            <label>AI Prompt</label>
            <textarea
              className="form-textarea"
              rows="3"
              value={template.subject_instruction || ""}
              onChange={(e) => handleChange("subject_instruction", e.target.value)}
              placeholder="e.g. 3 to 6 words maximum. Lowercase or sentence case. No spam words (e.g. Scaling support at {company_name})."
            />
          </div>

          {/* AI context about company */}
          <div className="form-group">
            <label>AI context about company</label>
            <textarea
              className="form-textarea"
              rows="4"
              value={template.value_proposition || ""}
              onChange={(e) => handleChange("value_proposition", e.target.value)}
              placeholder="Summary of what Virtual Employee provides..."
            />
          </div>

          {/* Closing & Free Trial Pitch */}
          <div className="form-group">
            <label>Closing Pitch, Trial Offer & Signature (Fixed Body Section)</label>
            <div className="tags-bar">
              <span>Insert tag:</span>
              <span className="tag-badge" onClick={() => insertTag("{company_name}")}>+ {"{company_name}"}</span>
              <span className="tag-badge" onClick={() => insertTag("{sender_name}")}>+ {"{sender_name}"}</span>
              <span className="tag-badge" onClick={() => insertTag("{sender_title}")}>+ {"{sender_title}"}</span>
              <span className="tag-badge" onClick={() => insertTag("{sender_company}")}>+ {"{sender_company}"}</span>
              <span className="tag-badge" onClick={() => insertTag("[Virtual Employee Candidate Trial Portal](https://trials.virtualemployee.com/v2?utm_source=api&utm_medium=automation&utm_campaign=api_automation)")}>+ {"[Portal Link]"}</span>
            </div>
            <textarea
              className="form-textarea"
              rows="12"
              value={template.closing_body || ""}
              onChange={(e) => handleChange("closing_body", e.target.value)}
              placeholder="Free trial pitch, portal link, call to action, and signature..."
            />
          </div>

          {template.last_updated && (
            <div style={{ fontSize: "11px", color: "#94a3b8", textAlign: "right" }}>
              Last saved: {template.last_updated}
            </div>
          )}
        </div>

        {/* Live Preview Column */}
        <div className="card">
          <h3 className="card-title">
            <span>👁️</span> Live Email Preview (Simulation)
          </h3>
          <p className="card-desc">
            This is how a cold outreach email will look when delivered to a prospect inbox.
          </p>

          <div className="preview-box">
            <div className="preview-subject">
              <span style={{ color: "#64748b" }}>Subject: </span>
              Scaling support at {previewCompany}
            </div>

            <div style={{ marginBottom: "14px", color: "#64748b", fontSize: "12px" }}>
              From: {template.sender_name || "Sandipan Sarkar"} &lt;{template.sender_company ? "outreach@" + template.sender_company.toLowerCase().replace(/\s+/g, '') + ".com" : "outreach@virtualemployee.com"}&gt;
              <br />
              To: Alex (VP of Operations @ {previewCompany})
            </div>

            <div className="preview-body-text">
              Hi Alex,
              <br /><br />
              <span className="preview-hook-highlight">
                [Personalized Hook generated by AI observing {previewCompany}&apos;s recent hiring for Customer Support Specialists and European growth...]
              </span>
              <br /><br />
              <span className="preview-hook-highlight">
                [Pain Point Bridge generated by AI connecting their workload to our on-demand pre-vetted support talent...]
              </span>
              <br /><br />
              {renderFormattedPreview(previewClosing)}
            </div>
          </div>

          <div style={{ background: "#f1f5f9", padding: "12px", borderRadius: "8px", fontSize: "12px", color: "#475569", lineHeight: "1.5" }}>
            💡 <strong>How it works:</strong> The AI automatically writes the personalized <em>Hook</em> and <em>Bridge</em> tailored to the specific company, and then seamlessly attaches your exact <em>Closing Pitch & Free Trial Portal Link</em> below it.
          </div>
        </div>
      </div>
    </div>
  );
}
