const API_BASE = "/api";
const TOKEN_KEY = "spendwise_token";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set token(value) {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  },
};

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

function formatError(body, status) {
  const detail = body?.detail;
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{loc: [...], msg: "..."}]
    return detail.map((d) => `${d.loc?.slice(1).join(".") || "field"}: ${d.msg}`).join("; ");
  }
  return detail || `Request failed (${status})`;
}

async function request(method, path, { body, query } = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  Object.entries(query || {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
  });

  const headers = { Accept: "application/json" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth.token) headers.Authorization = `Bearer ${auth.token}`;

  const res = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return null;
  const data = await res.json().catch(() => null);

  if (!res.ok) {
    if (res.status === 401 && auth.token) onUnauthorized();
    throw new ApiError(res.status, formatError(data, res.status));
  }
  return data;
}

export const api = {
  // Auth
  register: (data) => request("POST", "/auth/register", { body: data }),
  login: (data) => request("POST", "/auth/login", { body: data }),
  logout: () => request("POST", "/auth/logout"),
  me: () => request("GET", "/auth/me"),

  // Expenses
  listExpenses: (query) => request("GET", "/expenses", { query }),
  expenseSummary: (query) => request("GET", "/expenses/summary", { query }),
  getExpense: (id) => request("GET", `/expenses/${id}`),
  createExpense: (data) => request("POST", "/expenses", { body: data }),
  updateExpense: (id, data) => request("PUT", `/expenses/${id}`, { body: data }),
  deleteExpense: (id) => request("DELETE", `/expenses/${id}`),

  // Categories
  listCategories: () => request("GET", "/categories"),
  createCategory: (data) => request("POST", "/categories", { body: data }),
  updateCategory: (id, data) => request("PUT", `/categories/${id}`, { body: data }),
  deleteCategory: (id) => request("DELETE", `/categories/${id}`),

  // Users (admin)
  listUsers: () => request("GET", "/users"),
  updateUser: (id, data) => request("PATCH", `/users/${id}`, { body: data }),
  deleteUser: (id) => request("DELETE", `/users/${id}`),
};
