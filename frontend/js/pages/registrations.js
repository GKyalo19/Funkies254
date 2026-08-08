import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { escapeHtml, formatDate, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

function createRegistrationCard(registration) {
  const { event } = registration;
  const card = document.createElement("article");
  card.className = "registration-item";
  card.innerHTML = `
    <div class="cover">
      <img src="${event.cover_image_url || "/assets/images/event-cover-default.jpg"}" alt="${escapeHtml(event.title)}" loading="lazy" />
    </div>
    <div class="body">
      <h3>${escapeHtml(event.title)}</h3>
      <div class="meta">📍 ${escapeHtml(event.location)}</div>
      <div class="meta">📅 ${formatDate(event.start_datetime)}</div>
      <div class="footer-row">
        <a class="btn btn-secondary btn-sm" href="/pages/event.html?slug=${encodeURIComponent(event.slug)}">View event</a>
        <button class="btn btn-danger btn-sm" data-registration-id="${registration.id}">Cancel</button>
      </div>
    </div>
  `;
  qs("button[data-registration-id]", card).addEventListener("click", async (clickEvent) => {
    clickEvent.stopPropagation();
    try {
      await api.delete(`/registrations/${registration.id}/`);
      toast.success("Registration cancelled.");
      card.remove();
    } catch (err) {
      toast.error(err.message);
    }
  });
  return card;
}

async function loadRegistrations() {
  const grid = qs("#registrations-grid");
  try {
    const data = await api.get("/registrations/");
    const active = data.results.filter((r) => r.status === "registered");
    if (active.length === 0) {
      grid.innerHTML = `<div class="empty-state">You haven't registered for any events yet.<br><a class="btn btn-primary" style="margin-top:16px;" href="/pages/event-listings.html">Browse events</a></div>`;
      return;
    }
    grid.innerHTML = "";
    active.forEach((registration) => grid.appendChild(createRegistrationCard(registration)));
  } catch (err) {
    toast.error(err.message);
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  await loadRegistrations();
}

init();
