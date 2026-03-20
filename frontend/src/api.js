const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").trim();

function buildApiUrl(path) {
  const normalizedPath = `/${String(path).replace(/^\/+/, "")}`;
  const apiPath = normalizedPath.startsWith("/api/") ? normalizedPath : `/api${normalizedPath}`;

  if (!API_BASE_URL) {
    return apiPath;
  }

  const normalizedBaseUrl = API_BASE_URL.replace(/\/+$/, "");
  const baseWithoutApi = normalizedBaseUrl.endsWith("/api")
    ? normalizedBaseUrl.slice(0, -4)
    : normalizedBaseUrl;

  return `${baseWithoutApi}${apiPath}`;
}

async function request(path, options = {}) {
  const response = await fetch(buildApiUrl(path), {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export function analyzeClaim(payload) {
  return request("/api/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchHistory() {
  return request("/api/history");
}

export function fetchResult(id) {
  return request(`/api/result/${id}`);
}

export function fetchHealth() {
  return request("/api/health");
}
