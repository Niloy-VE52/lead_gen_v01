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

  const keywordsVal = Array.isArray(config.keywords)
    ? config.keywords.join(", ")
    : config.keywords || "";

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
        <input
          type="text"
          value={keywordsVal}
          onChange={(e) => handleArrayInput("keywords", e.target.value)}
          placeholder="e.g. Support Specialist"
        />
      </div>

      <div className="config-field">
        <label>Location</label>
        <input
          type="text"
          value={config.location}
          onChange={(e) => set("location", e.target.value)}
          placeholder="e.g. Europe"
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
    </div>
  );
}
