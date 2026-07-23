export const BASE_URL = (process.env.REACT_APP_API_URL || "http://localhost:8000").replace(/\/$/, "");

export async function apiPost(path, body) {
  const urlPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${BASE_URL}${urlPath}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function apiGet(path) {
  const urlPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${BASE_URL}${urlPath}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

