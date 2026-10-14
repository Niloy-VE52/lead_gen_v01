import MultiSelect from "./MultiSelect";
import { AVAILABLE_ROLES } from "../constants/roles";

export default function ConfigPanel({ config, onChange }) {
  const set = (key, val) => onChange({ ...config, [key]: val });

  const handleArrayInput = (key, val) =>
    set(
      key,
      val
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    );

  const keywordsArray = Array.isArray(config.keywords)
    ? config.keywords
    : typeof config.keywords === "string"
    ? config.keywords.split(",").map((s) => s.trim()).filter(Boolean)
    : [];

  const expVal = Array.isArray(config.experience_levels)
    ? config.experience_levels.join(", ")
    : config.experience_levels || "";

  const wtVal = Array.isArray(config.work_types)
    ? config.work_types.join(", ")
    : config.work_types || "";

  return (
    <div className="config-grid">
      <div className="config-field">
        <label>Job Titles / Keywords</label>
        <MultiSelect
          options={AVAILABLE_ROLES}
          selected={keywordsArray}
          onChange={(val) => set("keywords", val)}
          placeholder="Select roles..."
        />
      </div>

      <div className="config-field">
        <label>Location</label>
        <input
          type="text"
          value={config.location}
          onChange={(e) => set("location", e.target.value)}
          placeholder="e.g. Europe, Germany, Asia"
        />
      </div>

      <div className="config-field">
        <label>Experience Levels</label>
        <input
          type="text"
          value={expVal}
          onChange={(e) => handleArrayInput("experience_levels", e.target.value)}
          placeholder="e.g. entry-level, associate"
        />
      </div>

      <div className="config-field">
        <label>Work Types</label>
        <input
          type="text"
          value={wtVal}
          onChange={(e) => handleArrayInput("work_types", e.target.value)}
          placeholder="e.g. remote, hybrid"
        />
      </div>

      <div className="config-field">
        <label>Max Items</label>
        <input
          type="number"
          value={config.max_items}
          onChange={(e) => set("max_items", parseInt(e.target.value) || 10)}
        />
      </div>

      <div className="config-field">
        <label>Min Employees</label>
        <input
          type="number"
          value={config.min_employees}
          onChange={(e) => set("min_employees", parseInt(e.target.value) || 50)}
        />
      </div>

      <div className="config-field">
        <label>Max Employees</label>
        <input
          type="number"
          value={config.max_employees}
          onChange={(e) => set("max_employees", parseInt(e.target.value) || 1000)}
        />
      </div>

      <div className="config-field">
        <label>Published Within</label>
        <select
          value={config.published_at}
          onChange={(e) => set("published_at", e.target.value)}
        >
          <option value="r86400">Last 24 hours</option>
          <option value="r604800">Last 7 days</option>
          <option value="r2592000">Last 30 days</option>
        </select>
      </div>

      {/* ── Outreach Delivery Settings ── */}
      <div className="outreach-settings-card">
        <div className="outreach-settings-header">
          <div className="outreach-settings-title">
            <span>✉️ Outreach Delivery Settings</span>
            <span className={`outreach-mode-pill ${config.outreach_mode === "live" ? "pill-live" : "pill-test"}`}>
              {config.outreach_mode === "live" ? "Live Production" : "Safety Sandbox"}
            </span>
          </div>
          <p className="outreach-settings-desc">
            Choose whether automated outreach emails are sent to a test sandbox or directly to real prospects.
          </p>
        </div>

        <div className="outreach-toggle-group">
          <label className={`outreach-toggle-option ${config.outreach_mode !== "live" ? "active" : ""}`}>
            <input
              type="radio"
              name="outreach_mode"
              value="test"
              checked={config.outreach_mode !== "live"}
              onChange={() => set("outreach_mode", "test")}
            />
            <div className="option-text">
              <strong>🛡️ Test Mode (Sandbox)</strong>
              <span>Redirect all outreach to your test inbox without emailing real prospects</span>
            </div>
          </label>

          <label className={`outreach-toggle-option ${config.outreach_mode === "live" ? "active" : ""}`}>
            <input
              type="radio"
              name="outreach_mode"
              value="live"
              checked={config.outreach_mode === "live"}
              onChange={() => set("outreach_mode", "live")}
            />
            <div className="option-text">
              <strong>🚀 Live Production</strong>
              <span>Send directly to real scraped decision-maker emails at KEEP companies</span>
            </div>
          </label>
        </div>

        {config.outreach_mode !== "live" ? (
          <div className="config-field outreach-email-field">
            <label>Test Recipient Email Address</label>
            <input
              type="email"
              value={config.test_email_recipient || "niloyvetesting54@gmail.com"}
              onChange={(e) => set("test_email_recipient", e.target.value)}
              placeholder="e.g. niloyvetesting54@gmail.com"
            />
            <span className="field-hint">
              🔒 Safe Sandbox Active: Every email generated by the pipeline will be delivered to this test address.
            </span>
          </div>
        ) : (
          <div className="outreach-live-warning">
            ⚠️ <strong>Live Outreach Active:</strong> Emails will be delivered directly to the verified email addresses of executives at KEEP companies.
          </div>
        )}
      </div>
    </div>
  );
}
