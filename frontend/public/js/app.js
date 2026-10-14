import { api, auth, setUnauthorizedHandler } from "./api.js";

const CURRENCY = "KZT";
const PAGE_SIZE = 10;

const state = {
  user: null,
  categories: [],
  view: "dashboard",
  page: { offset: 0, total: 0 },
  filters: {},
};

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

const ESC_MAP = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
// Every API value rendered via innerHTML must go through esc() to prevent XSS
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ESC_MAP[c]);

const moneyFmt = new Intl.NumberFormat("en-US", { style: "currency", currency: CURRENCY });
const money = (n) => moneyFmt.format(Number(n) || 0);

const isoDate = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const fmtDate = (s) =>
  new Date(`${s.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

const isAdmin = () => state.user?.role === "admin";

function toast(message, type = "success") {
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.classList.add("hide"), 3000);
  setTimeout(() => el.remove(), 3400);
}

function confirmDialog(text) {
  const dlg = $("#confirm-dialog");
  $("#confirm-text").textContent = text;
  dlg.returnValue = "";
  dlg.showModal();
  return new Promise((resolve) => {
    dlg.addEventListener("close", () => resolve(dlg.returnValue === "ok"), { once: true });
  });
}

async function withBusy(form, fn) {
  const btn = form.querySelector('[type="submit"]');
  btn.disabled = true;
  try {
    await fn();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    btn.disabled = false;
  }
}

function categoryBadge(cat) {
  if (!cat) return '<span class="cat-badge muted">Uncategorized</span>';
  return `<span class="cat-badge"><i style="background:${esc(cat.color)}"></i>${esc(cat.name)}</span>`;
}

// ---------- auth ----------
function showAuth() {
  state.user = null;
  $("#app-view").hidden = true;
  $("#auth-view").hidden = false;
}

async function showApp() {
  const user = state.user;
  $("#user-name").textContent = user.full_name;
  $("#user-role").textContent = user.role;
  $("#user-role").className = `badge badge-${user.role}`;
  document.body.classList.toggle("is-admin", isAdmin());
  $("#auth-view").hidden = true;
  $("#app-view").hidden = false;
  await loadCategories();
  switchView("dashboard");
}

setUnauthorizedHandler(() => {
  auth.token = null;
  toast("Session expired, please log in again", "error");
  showAuth();
});

$$("[data-auth-tab]").forEach((tab) =>
  tab.addEventListener("click", () => {
    const target = tab.dataset.authTab;
    $$("[data-auth-tab]").forEach((t) => t.classList.toggle("active", t === tab));
    $("#login-form").hidden = target !== "login";
    $("#register-form").hidden = target !== "register";
  }),
);

async function loginWith(email, password) {
  const { access_token } = await api.login({ email, password });
  auth.token = access_token;
  state.user = await api.me();
  await showApp();
}

$("#login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  withBusy(form, async () => {
    const data = Object.fromEntries(new FormData(form));
    await loginWith(data.email, data.password);
    form.reset();
    toast(`Welcome back, ${state.user.full_name}!`);
  });
});

$("#register-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  withBusy(form, async () => {
    const data = Object.fromEntries(new FormData(form));
    await api.register(data);
    await loginWith(data.email, data.password);
    form.reset();
    toast("Account created");
  });
});

$("#logout-btn").addEventListener("click", async () => {
  try {
    await api.logout();
  } catch {
    // token may already be invalid; log out locally anyway
  }
  auth.token = null;
  showAuth();
  toast("Logged out");
});

// ---------- navigation ----------
function switchView(view) {
  if (["categories", "users"].includes(view) && !isAdmin()) view = "dashboard";
  state.view = view;
  $$(".nav-link").forEach((l) => l.classList.toggle("active", l.dataset.view === view));
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${view}`));
  const loaders = {
    dashboard: loadDashboard,
    expenses: loadExpenses,
    categories: renderCategories,
    users: loadUsers,
  };
  loaders[view]().catch((err) => toast(err.message, "error"));
}

$$(".nav-link").forEach((l) => l.addEventListener("click", () => switchView(l.dataset.view)));

const refreshCurrentView = () => switchView(state.view);

// ---------- dashboard ----------
async function loadDashboard() {
  const now = new Date();
  const monthRange = {
    date_from: isoDate(new Date(now.getFullYear(), now.getMonth(), 1)),
    date_to: isoDate(new Date(now.getFullYear(), now.getMonth() + 1, 0)),
  };
  const [month, allTime, recent] = await Promise.all([
    api.expenseSummary(monthRange),
    api.expenseSummary(),
    api.listExpenses({ limit: 6 }),
  ]);

  $("#stat-month").textContent = money(month.total);
  $("#stat-total").textContent = money(allTime.total);
  $("#stat-count").textContent = allTime.count;
  $("#stat-top").textContent = allTime.by_category[0]?.name ?? "—";

  const max = Math.max(...month.by_category.map((c) => c.total), 1);
  $("#category-bars").innerHTML = month.by_category.length
    ? month.by_category
        .map(
          (c) => `
        <div class="bar-row">
          <div class="bar-label"><span>${esc(c.name)}</span><span>${money(c.total)}</span></div>
          <div class="bar-track"><div class="bar-fill" style="width:${(c.total / max) * 100}%;background:${esc(c.color)}"></div></div>
        </div>`,
        )
        .join("")
    : '<p class="empty">No expenses this month yet.</p>';

  $("#recent-list").innerHTML = recent.items.length
    ? recent.items
        .map(
          (e) => `
        <li>
          <div><strong>${esc(e.title)}</strong><div class="muted small">${fmtDate(e.spent_on)} · ${esc(e.category?.name ?? "Uncategorized")}</div></div>
          <span class="amount">${money(e.amount)}</span>
        </li>`,
        )
        .join("")
    : '<li class="empty">Nothing here yet — add your first expense.</li>';
}

// ---------- expenses ----------
async function loadExpenses() {
  const data = await api.listExpenses({
    ...state.filters,
    limit: PAGE_SIZE,
    offset: state.page.offset,
  });
  state.page.total = data.total;

  $("#expenses-body").innerHTML = data.items.length
    ? data.items
        .map(
          (e) => `
      <tr>
        <td class="nowrap">${fmtDate(e.spent_on)}</td>
        <td><strong>${esc(e.title)}</strong>${e.note ? `<div class="muted small">${esc(e.note)}</div>` : ""}</td>
        <td>${categoryBadge(e.category)}</td>
        <td class="admin-only small">${esc(e.owner.email)}</td>
        <td class="num amount">${money(e.amount)}</td>
        <td class="actions">
          <button class="btn btn-sm" data-edit="${e.id}" type="button">Edit</button>
          <button class="btn btn-sm btn-danger-ghost" data-delete="${e.id}" data-title="${esc(e.title)}" type="button">Delete</button>
        </td>
      </tr>`,
        )
        .join("")
    : '<tr><td colspan="6" class="empty">No expenses found.</td></tr>';

  const from = data.total ? state.page.offset + 1 : 0;
  const to = Math.min(state.page.offset + PAGE_SIZE, data.total);
  $("#pager-info").textContent = `${from}–${to} of ${data.total}`;
  $("#prev-page").disabled = state.page.offset === 0;
  $("#next-page").disabled = to >= data.total;
}

$("#prev-page").addEventListener("click", () => {
  state.page.offset = Math.max(0, state.page.offset - PAGE_SIZE);
  loadExpenses().catch((err) => toast(err.message, "error"));
});
$("#next-page").addEventListener("click", () => {
  state.page.offset += PAGE_SIZE;
  loadExpenses().catch((err) => toast(err.message, "error"));
});

$("#filters").addEventListener("submit", (e) => {
  e.preventDefault();
  state.filters = Object.fromEntries(new FormData(e.target));
  state.page.offset = 0;
  loadExpenses().catch((err) => toast(err.message, "error"));
});
$("#filters").addEventListener("reset", () => {
  state.filters = {};
  state.page.offset = 0;
  setTimeout(() => loadExpenses().catch((err) => toast(err.message, "error")));
});

$("#expenses-body").addEventListener("click", async (e) => {
  const editId = e.target.dataset.edit;
  const deleteId = e.target.dataset.delete;
  try {
    if (editId) {
      openExpenseDialog(await api.getExpense(editId));
    } else if (deleteId) {
      if (!(await confirmDialog(`Delete expense "${e.target.dataset.title}"?`))) return;
      await api.deleteExpense(deleteId);
      toast("Expense deleted");
      if (state.page.offset >= state.page.total - 1) {
        state.page.offset = Math.max(0, state.page.offset - PAGE_SIZE);
      }
      await loadExpenses();
    }
  } catch (err) {
    toast(err.message, "error");
  }
});

function openExpenseDialog(expense = null) {
  const form = $("#expense-form");
  form.reset();
  // form.elements avoids clashes with built-in form properties like form.id / form.title
  const f = form.elements;
  $("#expense-dialog-title").textContent = expense ? "Edit expense" : "New expense";
  f.id.value = expense?.id ?? "";
  f.title.value = expense?.title ?? "";
  f.amount.value = expense?.amount ?? "";
  f.spent_on.value = expense?.spent_on ?? isoDate(new Date());
  f.category_id.value = expense?.category_id ?? "";
  f.note.value = expense?.note ?? "";
  $("#expense-dialog").showModal();
}

$$('[data-action="new-expense"]').forEach((b) =>
  b.addEventListener("click", () => openExpenseDialog()),
);

$("#expense-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const f = form.elements;
  withBusy(form, async () => {
    const payload = {
      title: f.title.value.trim(),
      amount: Number(f.amount.value),
      spent_on: f.spent_on.value,
      category_id: f.category_id.value ? Number(f.category_id.value) : null,
      note: f.note.value.trim() || null,
    };
    const id = f.id.value;
    if (id) await api.updateExpense(id, payload);
    else await api.createExpense(payload);
    $("#expense-dialog").close();
    toast(id ? "Expense updated" : "Expense added");
    refreshCurrentView();
  });
});

// ---------- categories ----------
async function loadCategories() {
  state.categories = await api.listCategories();
  const options = state.categories
    .map((c) => `<option value="${c.id}">${esc(c.name)}</option>`)
    .join("");
  $('#filters [name="category_id"]').innerHTML = `<option value="">All categories</option>${options}`;
  $('#expense-form [name="category_id"]').innerHTML = `<option value="">Uncategorized</option>${options}`;
}

async function renderCategories() {
  await loadCategories();
  $("#categories-body").innerHTML = state.categories.length
    ? state.categories
        .map(
          (c) => `
      <tr>
        <td class="muted">#${c.id}</td>
        <td>${categoryBadge(c)}</td>
        <td><code>${esc(c.color)}</code></td>
        <td class="actions">
          <button class="btn btn-sm" data-edit="${c.id}" type="button">Edit</button>
          <button class="btn btn-sm btn-danger-ghost" data-delete="${c.id}" type="button">Delete</button>
        </td>
      </tr>`,
        )
        .join("")
    : '<tr><td colspan="4" class="empty">No categories.</td></tr>';
}

function openCategoryDialog(cat = null) {
  const form = $("#category-form");
  form.reset();
  const f = form.elements;
  $("#category-dialog-title").textContent = cat ? "Edit category" : "New category";
  f.id.value = cat?.id ?? "";
  f.name.value = cat?.name ?? "";
  f.color.value = cat?.color ?? "#6366f1";
  $("#category-dialog").showModal();
}

$('[data-action="new-category"]').addEventListener("click", () => openCategoryDialog());

$("#categories-body").addEventListener("click", async (e) => {
  const id = Number(e.target.dataset.edit || e.target.dataset.delete);
  if (!id) return;
  const cat = state.categories.find((c) => c.id === id);
  if (e.target.dataset.edit) return openCategoryDialog(cat);
  if (!(await confirmDialog(`Delete category "${cat.name}"? Its expenses become uncategorized.`)))
    return;
  try {
    await api.deleteCategory(id);
    toast("Category deleted");
    await renderCategories();
  } catch (err) {
    toast(err.message, "error");
  }
});

$("#category-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const form = e.target;
  const f = form.elements;
  withBusy(form, async () => {
    const payload = { name: f.name.value.trim(), color: f.color.value };
    const id = f.id.value;
    if (id) await api.updateCategory(id, payload);
    else await api.createCategory(payload);
    $("#category-dialog").close();
    toast(id ? "Category updated" : "Category created");
    await renderCategories();
  });
});

// ---------- users (admin) ----------
async function loadUsers() {
  const users = await api.listUsers();
  $("#users-body").innerHTML = users
    .map((u) => {
      const self = u.id === state.user.id;
      return `
      <tr data-id="${u.id}">
        <td class="muted">#${u.id}</td>
        <td>${esc(u.full_name)}${self ? ' <span class="muted small">(you)</span>' : ""}</td>
        <td>${esc(u.email)}</td>
        <td>
          <select data-field="role" ${self ? "disabled" : ""}>
            <option value="user" ${u.role === "user" ? "selected" : ""}>user</option>
            <option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option>
          </select>
        </td>
        <td><input type="checkbox" data-field="is_active" ${u.is_active ? "checked" : ""} ${self ? "disabled" : ""}></td>
        <td class="nowrap">${fmtDate(u.created_at)}</td>
        <td class="actions">${
          self
            ? ""
            : `<button class="btn btn-sm btn-danger-ghost" data-delete="${u.id}" data-email="${esc(u.email)}" type="button">Delete</button>`
        }</td>
      </tr>`;
    })
    .join("");
}

$("#users-body").addEventListener("change", async (e) => {
  const field = e.target.dataset.field;
  if (!field) return;
  const id = e.target.closest("tr").dataset.id;
  const value = field === "is_active" ? e.target.checked : e.target.value;
  try {
    await api.updateUser(id, { [field]: value });
    toast("User updated");
  } catch (err) {
    toast(err.message, "error");
    await loadUsers();
  }
});

$("#users-body").addEventListener("click", async (e) => {
  const id = e.target.dataset.delete;
  if (!id) return;
  if (!(await confirmDialog(`Delete user ${e.target.dataset.email} and all their expenses?`))) return;
  try {
    await api.deleteUser(id);
    toast("User deleted");
    await loadUsers();
  } catch (err) {
    toast(err.message, "error");
  }
});

// ---------- dialogs ----------
$$("[data-close]").forEach((b) => b.addEventListener("click", () => b.closest("dialog").close()));

// ---------- boot ----------
(async function init() {
  if (!auth.token) return showAuth();
  try {
    state.user = await api.me();
    await showApp();
  } catch {
    auth.token = null;
    showAuth();
  }
})();
