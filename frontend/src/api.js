// Thin fetch wrapper: attaches the JWT, refreshes it once on 401,
// and turns FastAPI error payloads into readable messages.

const API_URL = import.meta.env.VITE_API_URL ?? "/api";
const ACCESS_KEY = "accessToken";
const REFRESH_KEY = "refreshToken";

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

// ---- token storage ---------------------------------------------------------
const listeners = new Set();

export const tokens = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set({ access_token, refresh_token }) {
    localStorage.setItem(ACCESS_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
  },
  clear(reason) {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    listeners.forEach((fn) => fn(reason));
  },
  // Called when tokens are dropped (logout / expired session)
  onClear(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

// ---- error formatting --------------------------------------------------------
function formatError(data, status) {
  const detail = data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    // Pydantic validation errors: [{loc: ["body", "field"], msg: "..."}]
    return detail
      .map((e) => {
        const field = (e.loc ?? []).filter((p) => p !== "body").join(".");
        const msg = (e.msg ?? "").replace(/^Value error, /, "");
        return field ? `${field}: ${msg}` : msg;
      })
      .join("; ");
  }
  return `Request failed (${status})`;
}

// ---- refresh (single-flight) ------------------------------------------------
let refreshPromise = null;

async function refreshTokens() {
  const refresh = tokens.refresh;
  if (!refresh) return false;
  refreshPromise ??= fetch(`${API_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  })
    .then(async (res) => {
      if (!res.ok) return false;
      tokens.set(await res.json());
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

// ---- main request function -------------------------------------------------
export async function api(path, { method = "GET", body, auth = true, retry = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && tokens.access) headers.Authorization = `Bearer ${tokens.access}`;

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Network error: cannot reach the server", 0);
  }

  if (res.status === 401 && auth && tokens.access) {
    if (retry && (await refreshTokens())) {
      return api(path, { method, body, auth, retry: false });
    }
    tokens.clear("expired");
    throw new ApiError("Your session has expired. Please log in again.", 401);
  }

  if (res.status === 204) return null;

  let data = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!res.ok) {
    throw new ApiError(formatError(data, res.status), res.status, data);
  }
  return data;
}
