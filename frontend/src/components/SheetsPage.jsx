// ── Update these URLs when ready ──────────────────────────────
const SHEETS = [
  {
    title:       "Scraped Jobs",
    sheetName:   "Scaped_v6",
    description: "Raw scraped LinkedIn jobs enriched with Glassdoor reviews and Apollo funding data.",
    url:         "https://docs.google.com/spreadsheets/d/1dQ4Rc42xui8rrvdDgW3HfwbjLgTRUdUBdKBduLp19rY/edit?usp=sharing",
    color:       "#2563eb",
    colorBg:     "#eff4ff",
    colorBorder: "#c7d7fd",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="1.6"/>
        <path d="M3 9h18M3 15h18M9 3v18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
      </svg>
    ),
    stats: ["Job Title", "Company", "Location", "Funding Stage", "Reviews"],
  },
  {
    title:       "Scored Leads",
    sheetName:   "Score_Listing_v6",
    description: "LLM-scored leads with decision (KEEP / HOLD / REJECT) and priority ranking.",
    url:         "https://docs.google.com/spreadsheets/d/1lcbVl8-md3xRzJp34tRRf1e48udtu_UsF6AqEX7l2r0/edit?usp=sharing",
    color:       "#059669",
    colorBg:     "#ecfdf5",
    colorBorder: "#a7f3d0",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
        <path d="M9 11l3 3L22 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    ),
    stats: ["Total Score", "Decision", "Priority", "Execution Signal", "Company Fit"],
  },
];

const IconExternalLink = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M15 3h6v6M10 14L21 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export default function SheetsPage() {
  return (
    <div className="sheets-page">
      <div className="home-header">
        <div>
          <h1 className="home-title">Google Sheets</h1>
          <p className="home-subtitle">Direct links to your pipeline output sheets</p>
        </div>
      </div>

      <div className="sheets-grid">
        {SHEETS.map((sheet) => (
          <a
            key={sheet.sheetName}
            href={sheet.url}
            target="_blank"
            rel="noopener noreferrer"
            className="sheet-card"
            style={{ "--sheet-color": sheet.color, "--sheet-bg": sheet.colorBg, "--sheet-border": sheet.colorBorder }}
          >
            {/* Top accent bar */}
            <div className="sheet-card-bar" />

            <div className="sheet-card-body">
              {/* Icon + title */}
              <div className="sheet-card-header">
                <div className="sheet-card-icon" style={{ color: sheet.color, background: sheet.colorBg, border: `1px solid ${sheet.colorBorder}` }}>
                  {sheet.icon}
                </div>
                <div className="sheet-card-external">
                  <IconExternalLink />
                </div>
              </div>

              <div className="sheet-card-title">{sheet.title}</div>
              <div className="sheet-card-name">{sheet.sheetName}</div>
              <p className="sheet-card-desc">{sheet.description}</p>

              {/* Columns preview */}
              <div className="sheet-card-cols">
                <div className="sheet-card-cols-label">Columns include</div>
                <div className="sheet-card-tags">
                  {sheet.stats.map((s) => (
                    <span key={s} className="sheet-tag" style={{ background: sheet.colorBg, color: sheet.color, borderColor: sheet.colorBorder }}>
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* CTA */}
              <div className="sheet-card-cta" style={{ color: sheet.color }}>
                Open in Google Sheets <IconExternalLink />
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}