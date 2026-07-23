import { useState, useEffect, useCallback } from "react";
import { apiGet, apiPost } from "../api/client";

/* ── Icons ─────────────────────────────────────────────────── */

const IconMail = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
    <rect x="2" y="4" width="20" height="16" rx="2" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M2 7l10 6 10-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconSearch = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8"/>
    <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
  </svg>
);

const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconPlus = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
);

const IconBuilding = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
    <rect x="4" y="2" width="16" height="20" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
    <path d="M9 6h2M13 6h2M9 10h2M13 10h2M9 14h2M13 14h2M9 18h6" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
  </svg>
);

const IconRefresh = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
    <path d="M1 4v6h6M23 20v-6h-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10M23 14l-4.64 4.36A9 9 0 0 1 3.51 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const IconLinkedIn = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-4 0v7h-4v-7a6 6 0 0 1 6-6z" stroke="currentColor" strokeWidth="1.6"/>
    <rect x="2" y="9" width="4" height="12" stroke="currentColor" strokeWidth="1.6"/>
    <circle cx="4" cy="4" r="2" stroke="currentColor" strokeWidth="1.6"/>
  </svg>
);


/* ── Main Component ────────────────────────────────────────── */

export default function EmailFinderPage() {
  const [companies, setCompanies]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [searches, setSearches]       = useState({});   // companyName → { runId, status, contacts }
  const [savedEmails, setSavedEmails] = useState({});   // "companyName|personName" → true

  // ── Search & Filter State ─────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("ALL"); // ALL, HIGH, MEDIUM
  const [statusFilter, setStatusFilter]     = useState("ALL"); // ALL, UNSEARCHED, RUNNING, FOUND, NO_CONTACTS

  // ── Load KEEP companies on mount ──────────────────────
  const loadCompanies = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiGet("/keep-companies");
      // Keep companies in reverse order (newest on top)
      setCompanies(data.companies || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCompanies(); }, [loadCompanies]);

  // ── Poll for email finder status ──────────────────────
  useEffect(() => {
    const runningSearches = Object.entries(searches).filter(
      ([, s]) => s.status === "running"
    );
    if (runningSearches.length === 0) return;

    const timers = runningSearches.map(([companyName, search]) =>
      setInterval(async () => {
        try {
          const data = await apiGet(`/status/${search.runId}`);
          setSearches((prev) => ({
            ...prev,
            [companyName]: {
              ...prev[companyName],
              status: data.status,
              step: data.step,
              contacts: data.contacts || prev[companyName]?.contacts || [],
            },
          }));
        } catch (_) {}
      }, 3000)
    );

    return () => timers.forEach(clearInterval);
  }, [searches]);

  // ── Start email search for a company ──────────────────
  const findEmails = async (company) => {
    if (!company.companyUrl) {
      setSearches((prev) => ({
        ...prev,
        [company.companyName]: {
          status: "error",
          step: "No LinkedIn company URL found",
          contacts: [],
        },
      }));
      return;
    }

    try {
      const res = await apiPost("/find-emails", {
        company_url: company.companyUrl,
        company_name: company.companyName,
      });

      setSearches((prev) => ({
        ...prev,
        [company.companyName]: {
          runId: res.run_id,
          status: "running",
          step: "Starting...",
          contacts: [],
        },
      }));
    } catch (e) {
      setSearches((prev) => ({
        ...prev,
        [company.companyName]: {
          status: "error",
          step: e.message,
          contacts: [],
        },
      }));
    }
  };

  // ── Save a contact ────────────────────────────────────
  const saveContact = async (contact) => {
    const key = `${contact.companyName}|${contact.personName}`;
    try {
      await apiPost("/save-email", {
        companyName: contact.companyName,
        personName: contact.personName,
        email: contact.email,
        designation: contact.designation,
        linkedinUrl: contact.linkedinUrl,
      });
      setSavedEmails((prev) => ({ ...prev, [key]: true }));
    } catch (e) {
      alert(`Failed to save: ${e.message}`);
    }
  };

  // ── Filtering Logic ───────────────────────────────────
  const filteredCompanies = companies.filter((company) => {
    // 1. Search Query filter (matches companyName, location, sector)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchName = company.companyName.toLowerCase().includes(q);
      const matchLoc  = (company.location || "").toLowerCase().includes(q);
      const matchSec  = (company.sector || "").toLowerCase().includes(q);
      if (!matchName && !matchLoc && !matchSec) return false;
    }

    // 2. Priority Filter
    if (priorityFilter !== "ALL") {
      const prio = (company.priority || "").toUpperCase();
      if (prio !== priorityFilter) return false;
    }

    // 3. Status Filter
    if (statusFilter !== "ALL") {
      const search = searches[company.companyName];
      if (statusFilter === "UNSEARCHED" && search) return false;
      if (statusFilter === "RUNNING" && search?.status !== "running") return false;
      if (statusFilter === "FOUND" && (!search || search.status !== "done" || (search.contacts || []).length === 0)) return false;
      if (statusFilter === "NO_CONTACTS" && (!search || search.status !== "done" || (search.contacts || []).length > 0)) return false;
    }

    return true;
  });

  // ── Render ────────────────────────────────────────────
  return (
    <div className="email-finder-page">
      {/* Header */}
      <div className="home-header">
        <div>
          <h1 className="home-title">Email Finder</h1>
          <p className="home-subtitle">Find decision makers & emails for KEEP-scored companies (newest first)</p>
        </div>
        <button className="btn-secondary ef-refresh-btn" onClick={loadCompanies} disabled={loading}>
          <IconRefresh /> Refresh
        </button>
      </div>

      {/* Toolbar: Search + Filters */}
      {!loading && !error && companies.length > 0 && (
        <div className="ef-toolbar">
          {/* Search bar */}
          <div className="ef-search-box">
            <IconSearch />
            <input
              type="text"
              placeholder="Search company, location, or sector..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="ef-clear-search" onClick={() => setSearchQuery("")}>
                ✕
              </button>
            )}
          </div>

          {/* Filters */}
          <div className="ef-filters">
            <div className="ef-filter-group">
              <label>Priority:</label>
              <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
                <option value="ALL">All Priorities</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
              </select>
            </div>

            <div className="ef-filter-group">
              <label>Status:</label>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                <option value="ALL">All Statuses</option>
                <option value="UNSEARCHED">Not Searched</option>
                <option value="RUNNING">Searching...</option>
                <option value="FOUND">Emails Found</option>
                <option value="NO_CONTACTS">No Contacts</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Summary stats line */}
      {!loading && !error && companies.length > 0 && (
        <div className="ef-summary-bar">
          Showing <strong>{filteredCompanies.length}</strong> of <strong>{companies.length}</strong> KEEP companies
          {companies.length > 0 && <span className="ef-stack-badge">⚡ Stacked: Newest First</span>}
        </div>
      )}

      {/* Loading / Error / Empty */}
      {loading && (
        <div className="ef-loading">
          <div className="ef-loading-spinner" />
          <span>Loading KEEP companies from scoring sheet...</span>
        </div>
      )}

      {error && (
        <div className="error-msg">⚠️ {error}</div>
      )}

      {!loading && !error && companies.length === 0 && (
        <div className="empty-monitor">
          <div className="empty-monitor-icon"><IconBuilding /></div>
          <div className="empty-monitor-text">
            No KEEP-scored companies found.<br />
            Run the scoring pipeline first, then come back here.
          </div>
        </div>
      )}

      {!loading && !error && companies.length > 0 && filteredCompanies.length === 0 && (
        <div className="empty-monitor">
          <div className="empty-monitor-icon"><IconSearch /></div>
          <div className="empty-monitor-text">
            No companies match your search/filter criteria.
          </div>
        </div>
      )}

      {/* Company Cards Stack */}
      {!loading && filteredCompanies.length > 0 && (
        <div className="ef-companies">
          {filteredCompanies.map((company, index) => {
            const search = searches[company.companyName];
            const isRunning = search?.status === "running";
            const isDone = search?.status === "done";
            const isError = search?.status === "error";
            const contacts = search?.contacts || [];
            const isNewest = index === 0 && searchQuery === "" && priorityFilter === "ALL" && statusFilter === "ALL";

            return (
              <div key={company.companyName} className={`ef-company-card ${isNewest ? "ef-newest-card" : ""}`}>
                {/* Company header */}
                <div className="ef-company-header">
                  <div className="ef-company-info">
                    <div className="ef-company-icon">
                      <IconBuilding />
                    </div>
                    <div>
                      <div className="ef-company-name-row">
                        <span className="ef-company-name">{company.companyName}</span>
                        {isNewest && <span className="ef-tag-new">LATEST KEEP</span>}
                      </div>
                      <div className="ef-company-meta">
                        {company.location && <span>{company.location}</span>}
                        {company.sector && <span>• {company.sector}</span>}
                        {company.priority && (
                          <span className={`ef-priority ef-priority-${company.priority.toLowerCase()}`}>
                            {company.priority}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="ef-company-actions">
                    {!search && (
                      <button className="btn-launch ef-find-btn" onClick={() => findEmails(company)}>
                        <IconSearch /> Find Emails
                      </button>
                    )}
                    {isRunning && (
                      <div className="ef-status-pill ef-status-running">
                        <div className="launch-spinner" /> {search.step}
                      </div>
                    )}
                    {isDone && (
                      <div className="ef-status-pill ef-status-done">
                        <IconCheck /> {contacts.length} contacts found
                      </div>
                    )}
                    {isError && (
                      <div className="ef-status-pill ef-status-error">
                        ⚠️ {search.step}
                      </div>
                    )}
                  </div>
                </div>

                {/* Running progress bar */}
                {isRunning && <div className="pulse-bar" />}

                {/* Contacts table */}
                {isDone && contacts.length > 0 && (
                  <div className="ef-contacts-section">
                    <div className="ef-contacts-label">
                      <IconMail /> Decision Makers
                    </div>
                    <table className="ef-contacts-table">
                      <thead>
                        <tr>
                          <th>Person</th>
                          <th>Designation</th>
                          <th>Email</th>
                          <th>LinkedIn</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {contacts.map((contact, idx) => {
                          const saveKey = `${contact.companyName}|${contact.personName}`;
                          const isSaved = savedEmails[saveKey];

                          return (
                            <tr key={idx}>
                              <td className="ef-td-name">{contact.personName}</td>
                              <td className="ef-td-designation">{contact.designation || "—"}</td>
                              <td className="ef-td-email">
                                {contact.email ? (
                                  <a href={`mailto:${contact.email}`}>{contact.email}</a>
                                ) : (
                                  <span className="ef-no-email">No email found</span>
                                )}
                              </td>
                              <td>
                                {contact.linkedinUrl ? (
                                  <a
                                    href={contact.linkedinUrl}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="ef-linkedin-link"
                                  >
                                    <IconLinkedIn /> Profile
                                  </a>
                                ) : "—"}
                              </td>
                              <td>
                                {isSaved ? (
                                  <span className="ef-saved-badge">
                                    <IconCheck /> Added
                                  </span>
                                ) : (
                                  <button
                                    className="ef-add-btn"
                                    onClick={() => saveContact(contact)}
                                    disabled={!contact.email}
                                    title={!contact.email ? "No email to save" : "Add to Email Saver sheet"}
                                  >
                                    <IconPlus /> ADD
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Done but no contacts */}
                {isDone && contacts.length === 0 && (
                  <div className="ef-no-contacts">
                    No decision makers found for this company.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

