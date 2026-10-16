export const BASE_URL = (process.env.REACT_APP_API_URL || "http://localhost:8000").replace(/\/$/, "");

export async function apiPost(path, body) {
  const urlPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${BASE_URL}${urlPath}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) msg = errData.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

export async function apiGet(path) {
  const urlPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${BASE_URL}${urlPath}`);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) msg = errData.detail;
    } catch (_) {}
    throw new Error(msg);
  }
  return res.json();
}

