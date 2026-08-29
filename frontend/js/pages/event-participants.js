import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { canManageEvents, requireAuth } from "../utils/auth.js";
import { escapeHtml, formatDate, getQueryParam, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  if (!canManageEvents(user)) {
    document.querySelector("main").innerHTML = `<div class="empty-state">Only institution staff and administrators can view participants.</div>`;
    return;
  }

  const slug = getQueryParam("slug");
  if (!slug) {
    qs("#participants-body").innerHTML = `<tr><td colspan="5">Missing event.</td></tr>`;
    return;
  }

  try {
    const event = await api.get(`/events/${slug}/`);
    qs("#participants-heading").textContent = event.title;
    qs("#participants-intro").textContent = `${event.registration_count ?? 0} registered · ${event.institution?.name || ""}`;
    qs("#back-to-event").href = `/pages/event.html?slug=${encodeURIComponent(event.slug)}`;

    const data = await api.get(`/events/${event.id}/registrations/`);
    const rows = data.results || [];
    if (!rows.length) {
      qs("#participants-body").innerHTML = `<tr><td colspan="5">Nobody has registered yet.</td></tr>`;
      return;
    }
    qs("#participants-body").innerHTML = rows
      .map(
        (row) => `
        <tr>
          <td>${escapeHtml(row.user?.name || "")}</td>
          <td>${escapeHtml(row.user?.email || "")}</td>
          <td>${escapeHtml(row.user?.institution_affiliation || "—")}</td>
          <td>${escapeHtml(row.status || "")}</td>
          <td>${escapeHtml(formatDate(row.registered_at))}</td>
        </tr>`
      )
      .join("");
  } catch (err) {
    qs("#participants-body").innerHTML = `<tr><td colspan="5">Could not load participants.</td></tr>`;
    toast.error(err instanceof ApiError ? err.message : "Could not load participants.");
  }
}

init();
