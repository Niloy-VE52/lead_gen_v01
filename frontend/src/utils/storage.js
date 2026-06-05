const STORAGE_KEY = "leadgen_runs";
const THREE_MONTHS_MS = 90 * 24 * 60 * 60 * 1000;

export function saveRuns(runs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
  } catch (e) {
    console.warn("localStorage write failed:", e);
  }
}

export function loadRuns() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const runs = JSON.parse(raw);
    const cutoff = Date.now() - THREE_MONTHS_MS;

    return runs
      .filter((r) => !r.timestamp || r.timestamp > cutoff)
      .map((r) => ({
        ...r,
        // A run can't still be "running" after a page refresh
        status: r.status === "running" ? "unknown" : r.status,
        step:   r.status === "running" ? "Status unknown — reloaded during run" : r.step,
      }));
  } catch (e) {
    console.warn("localStorage read failed:", e);
    return [];
  }
}

export function clearRuns() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (e) {}
}