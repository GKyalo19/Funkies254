import { renderFooter } from "../components/footer.js";
import { renderEventGrid, toEventList } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { escapeHtml, formatDate, qs } from "../utils/dom.js";
import { coverInnerHtml } from "../utils/media.js";
import { toast } from "../utils/toast.js";

function createRegistrationCard(registration) {
  const { event } = registration;
  const card = document.createElement("article");
  card.className = "registration-item";
  card.innerHTML = `
    <div class="cover">
      ${coverInnerHtml(event.cover_image_url, event.title)}
    </div>
    <div class="body">
      <h3>${escapeHtml(event.title)}</h3>
      <div class="meta">📍 ${escapeHtml(event.is_virtual ? "Virtual event" : event.location || event.venue || "Venue TBC")}</div>
      <div class="meta">📅 ${formatDate(event.start_time)}</div>
      <div class="footer-row">
        <a class="btn btn-secondary btn-sm" href="/pages/event.html?slug=${encodeURIComponent(event.slug)}">View event</a>
        <button class="btn btn-danger btn-sm" data-registration-id="${escapeHtml(registration.id)}">Cancel</button>
      </div>
    </div>
  `;
  qs("button[data-registration-id]", card).addEventListener("click", async (clickEvent) => {
    const button = clickEvent.currentTarget;
    button.disabled = true;
    try {
      await api.post(`/registrations/${registration.id}/cancel/`);
      toast.success("Registration cancelled.");
      card.remove();
      if (!qs("#registrations-grid").querySelector(".registration-item")) renderEmptyState();
    } catch (err) {
      toast.error(err.message);
      button.disabled = false;
    }
  });
  return card;
}

function renderEmptyState() {
  qs("#registrations-grid").innerHTML = `<div class="empty-state">You haven't registered for any events yet.<br><a class="btn btn-primary" style="margin-top:16px;" href="/pages/event-listings.html">Browse events</a></div>`;
}

async function loadRegistrations() {
  const grid = qs("#registrations-grid");
  try {
    // `status=registered` filters out anything already cancelled or attended.
    const data = await api.get("/users/me/registrations/?status=registered");
    const active = data.results || [];
    if (active.length === 0) {
      renderEmptyState();
      return;
    }
    grid.innerHTML = "";
    active.forEach((registration) => grid.appendChild(createRegistrationCard(registration)));
  } catch (err) {
    toast.error(err.message);
  }
}

async function loadSavedEvents() {
  try {
    const data = await api.get("/users/me/saved-events/");
    renderEventGrid(qs("#saved-events-grid"), toEventList(data), "Nothing saved yet — tap “Save for later” on any event.");
  } catch (err) {
    qs("#saved-events-section").style.display = "none";
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  await loadRegistrations();
  await loadSavedEvents();
}

init();
