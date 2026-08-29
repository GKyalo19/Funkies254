import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { canManageEvents, isAdmin, isInstitutionStaff, requireAuth } from "../utils/auth.js";
import { escapeHtml, formatDate, qs } from "../utils/dom.js";
import { coverInnerHtml } from "../utils/media.js";
import { toast } from "../utils/toast.js";

let currentUser = null;
let verifiedFilter = "";

function eventsQuery() {
  const params = new URLSearchParams({ page_size: "50" });
  if (isInstitutionStaff(currentUser)) {
    params.set("mine", "true");
  }
  if (verifiedFilter !== "") params.set("is_verified", verifiedFilter);
  return `/events/?${params.toString()}`;
}

function createManageCard(event) {
  const card = document.createElement("article");
  card.className = "registration-item";
  const verifiedLabel = event.is_verified ? "Verified" : "Awaiting verification";
  card.innerHTML = `
    <div class="cover">
      ${coverInnerHtml(event.cover_image_url, event.title)}
    </div>
    <div class="body">
      <h3>${escapeHtml(event.title)}</h3>
      <div class="meta">${escapeHtml(event.institution?.name || "No institution")}</div>
      <div class="meta">${formatDate(event.start_time)} · ${event.registration_count ?? 0} registered</div>
      <div class="meta">${escapeHtml(verifiedLabel)}</div>
      <div class="footer-row">
        <a class="btn btn-secondary btn-sm" href="/pages/event.html?slug=${encodeURIComponent(event.slug)}">View</a>
        <a class="btn btn-secondary btn-sm" href="/pages/event-form.html?slug=${encodeURIComponent(event.slug)}">Edit</a>
        <a class="btn btn-secondary btn-sm" href="/pages/event-participants.html?slug=${encodeURIComponent(event.slug)}">Participants</a>
        ${
          isAdmin(currentUser)
            ? `<button type="button" class="btn btn-sm ${event.is_verified ? "btn-secondary" : "btn-gold"}" data-verify="${event.is_verified ? "false" : "true"}">${event.is_verified ? "Unverify" : "Verify"}</button>`
            : ""
        }
      </div>
    </div>
  `;

  const verifyBtn = card.querySelector("[data-verify]");
  if (verifyBtn) {
    verifyBtn.addEventListener("click", async () => {
      verifyBtn.disabled = true;
      try {
        await api.post(`/events/${event.slug}/verify/`, {
          verified: verifyBtn.dataset.verify === "true",
        });
        toast.success(event.is_verified ? "Event unmarked as verified." : "Event verified.");
        await loadEvents();
      } catch (err) {
        toast.error(err instanceof ApiError ? err.message : "Could not update verification.");
        verifyBtn.disabled = false;
      }
    });
  }
  return card;
}

async function loadEvents() {
  const grid = qs("#events-grid");
  grid.innerHTML = `<div class="empty-state">Loading events…</div>`;
  try {
    const data = await api.get(eventsQuery());
    const events = data.results || [];
    if (events.length === 0) {
      grid.innerHTML = `<div class="empty-state">No events yet. <a href="/pages/event-form.html">Create one</a>.</div>`;
      return;
    }
    grid.innerHTML = "";
    events.forEach((event) => grid.appendChild(createManageCard(event)));
  } catch (err) {
    grid.innerHTML = "";
    toast.error(err instanceof ApiError ? err.message : "Could not load events.");
  }
}

function wireFilters() {
  const bar = qs("#dashboard-filters");
  bar.hidden = false;
  bar.querySelectorAll("[data-verified]").forEach((btn) => {
    btn.addEventListener("click", () => {
      verifiedFilter = btn.dataset.verified;
      bar.querySelectorAll(".filter-tag").forEach((el) => el.classList.remove("active"));
      btn.classList.add("active");
      loadEvents();
    });
  });
}

async function init() {
  await renderHeader();
  renderFooter();

  currentUser = await requireAuth();
  if (!currentUser) return;

  if (!canManageEvents(currentUser)) {
    document.querySelector("main").innerHTML = `<div class="empty-state">This page is for institution staff and administrators.</div>`;
    return;
  }

  if (isInstitutionStaff(currentUser)) {
    qs("#dashboard-heading").textContent = "My Events";
    qs("#dashboard-intro").textContent = "Events you created. Open a card to edit it or see who registered.";
  } else {
    qs("#dashboard-heading").textContent = "All Events";
    qs("#dashboard-intro").textContent = "Platform-wide listings. Verify events so they appear in the student feed.";
    wireFilters();
  }

  await loadEvents();
}

init();
