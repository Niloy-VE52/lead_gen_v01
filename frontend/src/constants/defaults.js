export const DEFAULT_CONFIG = {
  keywords: ["Customer Support Specialist"],
  location: ["Europe"],
  experience_levels: ["entry-level", "associate"],
  work_types: ["Remote"],
  published_at: "r604800",
  max_items: 10,
  min_employees: 50,
  max_employees: 1000,
  outreach_mode: "test", // "test" (safe redirect) or "live" (real prospect emails)
  test_email_recipient: "niloyvetesting54@gmail.com",
  apify_mode: "test",    // "test" (numbered free pool) or "live" (single premium key)
};

export const PIPELINE_STEPS = [
  { num: "1", label: "LinkedIn Scraper",    color: "accent2" },
  { num: "2", label: "Repeatability Check", color: "accent2" },
  { num: "3", label: "Glassdoor Reviews",   color: "accent2" },
  { num: "4", label: "Apollo Funding",      color: "accent2" },
  { num: "5", label: "Lead Scoring (LLM)", color: "accent"  },
  { num: "6", label: "Google Sheets Save",  color: "accent"  },
];
