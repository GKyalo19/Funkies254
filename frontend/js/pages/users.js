import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { isAdmin, isSuperAdmin, requireAuth } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const ROLE_LABELS = {
  student: "Student",
  institution_staff: "Staff",
  admin: "Admin",
  super_admin: "Super admin",
};

let currentUser = null;

function usersQuery() {
  const params = new URLSearchParams({ page_size: "50" });
  const search = qs("#user-search").value.trim();
  const role = qs("#user-role").value;
  if (search) params.set("search", search);
  if (role) params.set("role", role);
  return `/users/?${params.toString()}`;
}

function roleSelect(user) {
  const options = Object.entries(ROLE_LABELS)
    .map(
      ([value, label]) =>
        `<option value="${value}" ${value === user.role ? "selected" : ""}>${label}</option>`
    )
    .join("");
  return `<select class="role-select" data-user-id="${escapeHtml(user.id)}">${options}</select>`;
}

function renderRows(users) {
  const body = qs("#users-body");
  if (!users.length) {
    body.innerHTML = `<tr><td colspan="6">No accounts match those filters.</td></tr>`;
    return;
  }

  body.innerHTML = users
    .map((user) => {
      const isSelf = user.id === currentUser.id;
      const roleCell =
        isSuperAdmin(currentUser) && !isSelf
          ? roleSelect(user)
          : escapeHtml(ROLE_LABELS[user.role] || user.role);
      const saveBtn = isSuperAdmin(currentUser)
        ? `<button type="button" class="btn btn-gold btn-sm" data-save="${escapeHtml(user.id)}">Save</button>`
        : "";
      return `
        <tr data-row="${escapeHtml(user.id)}" data-role="${escapeHtml(user.role)}">
          <td>
            ${
              isSuperAdmin(currentUser)
                ? `<input type="text" class="table-input" data-field="name" value="${escapeHtml(user.name || "")}" />`
                : escapeHtml(user.name || "")
            }
          </td>
          <td>${escapeHtml(user.email)}</td>
          <td>
            ${
              isSuperAdmin(currentUser)
                ? `<input type="text" class="table-input" data-field="institution_affiliation" value="${escapeHtml(user.institution_affiliation || "")}" />`
                : escapeHtml(user.institution_affiliation || "—")
            }
          </td>
          <td>${escapeHtml(user.institution_name || user.institution?.name || "—")}</td>
          <td>${roleCell}</td>
          <td>${saveBtn}</td>
        </tr>
      `;
    })
    .join("");

  body.querySelectorAll("[data-save]").forEach((btn) => {
    btn.addEventListener("click", () => saveUser(btn.dataset.save, btn.closest("tr")));
  });
}

async function saveUser(userId, row) {
  const name = qs('[data-field="name"]', row)?.value.trim();
  const affiliation = qs('[data-field="institution_affiliation"]', row)?.value.trim() || null;
  const role = qs(".role-select", row)?.value;
  const saveBtn = qs("[data-save]", row);
  saveBtn.disabled = true;

  try {
    await api.patch(`/users/${userId}/`, {
      name,
      institution_affiliation: affiliation,
    });
    if (role && role !== row.dataset.role) {
      await api.post(`/users/${userId}/role/`, { role });
    }
    toast.success("Account updated.");
    await loadUsers();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not update that account.");
    saveBtn.disabled = false;
  }
}

async function loadUsers() {
  try {
    const data = await api.get(usersQuery());
    renderRows(data.results || []);
  } catch (err) {
    qs("#users-body").innerHTML = `<tr><td colspan="6">Could not load users.</td></tr>`;
    toast.error(err instanceof ApiError ? err.message : "Could not load users.");
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  currentUser = await requireAuth();
  if (!currentUser) return;

  if (!isAdmin(currentUser)) {
    document.querySelector("main").innerHTML = `<div class="empty-state">Only administrators can view accounts.</div>`;
    return;
  }

  if (isSuperAdmin(currentUser)) {
    qs("#users-intro").textContent =
      "Change a person's role here. Promoting someone to staff uses their school name (or a linked institution) so they can create events.";
  }

  qs("#user-filters").addEventListener("submit", (event) => {
    event.preventDefault();
    loadUsers();
  });

  await loadUsers();
}

init();
