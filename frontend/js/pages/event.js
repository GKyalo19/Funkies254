import { renderFooter } from "../components/footer.js";
import { renderEventGrid, toEventList } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { getCurrentUser, initials, isStudent } from "../utils/auth.js";
import { escapeHtml, formatDate, formatTimeRange, getQueryParam, qs } from "../utils/dom.js";
import { avatarInnerHtml, coverInnerHtml } from "../utils/media.js";
import { toast } from "../utils/toast.js";

const slug = getQueryParam("slug");
const content = qs("#event-content");

let currentUser = null;

function institutionRowHtml(institution) {
  if (!institution) return "";
  return `
    <div class="organizer-row">
      <div class="avatar">
        ${avatarInnerHtml(institution.logo_url) || initials({ name: institution.name })}
      </div>
      <div class="info">
        <h4>by ${escapeHtml(institution.name)}</h4>
        <p class="stats">
          ${escapeHtml(institution.location || "Kenya")}
          ${institution.verified ? " &middot; ✓ Verified institution" : ""}
        </p>
      </div>
      <div class="actions">
        <a class="btn btn-secondary" href="/pages/event-listings.html?institution_slug=${encodeURIComponent(institution.slug)}">More from this school</a>
      </div>
    </div>
  `;
}

function actionCardHtml(event) {
  const attendees = `<p class="spots">${event.registration_count} registered</p>`;

  // Events that point at an external sign-up form are informational here: the
  // API deliberately has no internal registration for them.
  if (event.registration_link) {
    return `
      <div class="registration-card">
        <h4>${escapeHtml(event.is_virtual ? "Virtual event" : event.venue || event.location || "Venue TBC")}</h4>
        ${attendees}
        <a class="btn btn-gold btn-block" href="${escapeHtml(event.registration_link)}" target="_blank" rel="noopener">Register externally</a>
        ${saveButtonHtml(event)}
      </div>
    `;
  }

  if (!currentUser) {
    return `
      <div class="registration-card">
        <h4>${escapeHtml(event.venue || event.location || "Venue TBC")}</h4>
        ${attendees}
        <a class="btn btn-gold btn-block" href="/pages/login.html">Log in to register</a>
      </div>
    `;
  }

  if (!isStudent(currentUser)) {
    return `
      <div class="registration-card">
        <h4>${escapeHtml(event.venue || event.location || "Venue TBC")}</h4>
        ${attendees}
        <p class="spots">Staff and admin accounts don't register for events.</p>
      </div>
    `;
  }

  return `
    <div class="registration-card">
      <h4>${escapeHtml(event.venue || event.location || "Venue TBC")}</h4>
      ${attendees}
      <button class="btn btn-block ${event.is_registered ? "btn-danger" : "btn-gold"}" id="register-btn">
        ${event.is_registered ? "Cancel registration" : "Register"}
      </button>
      ${saveButtonHtml(event)}
    </div>
  `;
}

function saveButtonHtml(event) {
  if (!currentUser || !isStudent(currentUser)) return "";
  return `
    <button class="btn btn-secondary btn-block" id="save-btn" style="margin-top:10px;">
      ${event.is_saved ? "★ Saved" : "☆ Save for later"}
    </button>
  `;
}

function locationLineHtml(event) {
  if (event.is_virtual) {
    return `
      <div class="info-row">
        <div class="icon"><img src="/assets/icons/icon-location.svg" alt="" /></div>
        <div>
          <strong>Virtual event</strong>
          <p style="margin:2px 0 0;color:var(--color-text-muted);">Join online using the registration link</p>
        </div>
      </div>
    `;
  }
  return `
    <div class="info-row">
      <div class="icon"><img src="/assets/icons/icon-location.svg" alt="" /></div>
      <div>
        <strong>${escapeHtml(event.venue || "Venue to be confirmed")}</strong>
        <p style="margin:2px 0 0;color:var(--color-text-muted);">${escapeHtml(event.location || "")}</p>
      </div>
    </div>
  `;
}

function renderEvent(event) {
  const description = escapeHtml(event.description);
  const isLong = description.length > 260;
  const shortDescription = isLong ? `${description.slice(0, 260)}&hellip;` : description;

  content.innerHTML = `
    <div class="event-hero">
      ${coverInnerHtml(event.cover_image_url, event.title)}
    </div>

    ${institutionRowHtml(event.institution)}

    <div class="event-detail-layout">
      <div>
        <div class="categories" style="margin-bottom:12px;">
          ${event.categories.map((c) => `<span class="pill">${escapeHtml(c.name)}</span>`).join("")}
          ${event.school_level ? `<span class="pill">${escapeHtml(event.school_level.name)}</span>` : ""}
        </div>
        <h1 class="event-title">${escapeHtml(event.title)}</h1>

        <div class="event-info-list" style="margin:24px 0;">
          ${locationLineHtml(event)}
          <div class="info-row">
            <div class="icon"><img src="/assets/icons/icon-calendar.svg" alt="" /></div>
            <div>
              <strong>${formatDate(event.start_time)}</strong>
              <p style="margin:2px 0 0;color:var(--color-text-muted);">${formatTimeRange(event.start_time, event.end_time)}</p>
            </div>
          </div>
        </div>

        <div class="event-body-text">
          <h3>Overview</h3>
          <p id="event-description">${shortDescription}</p>
          ${isLong ? `<a class="read-more-link" id="read-more-btn" href="#" data-full="${description}" data-short="${shortDescription}">Read more</a>` : ""}

          ${event.is_virtual ? "" : `<h3>Location</h3><p>${escapeHtml([event.venue, event.location].filter(Boolean).join(" · ") || "To be confirmed")}</p>`}
        </div>
      </div>

      <div>${actionCardHtml(event)}</div>
    </div>
  `;

  const registerBtn = qs("#register-btn", content);
  if (registerBtn) registerBtn.addEventListener("click", () => handleRegister(event));

  const saveBtn = qs("#save-btn", content);
  if (saveBtn) saveBtn.addEventListener("click", () => handleSave(event));

  const readMoreBtn = qs("#read-more-btn", content);
  if (readMoreBtn) {
    readMoreBtn.addEventListener("click", (evt) => {
      evt.preventDefault();
      const descEl = qs("#event-description", content);
      const expanded = readMoreBtn.dataset.expanded === "true";
      descEl.innerHTML = expanded ? readMoreBtn.dataset.short : readMoreBtn.dataset.full;
      readMoreBtn.textContent = expanded ? "Read more" : "Show less";
      readMoreBtn.dataset.expanded = expanded ? "false" : "true";
    });
  }
}

async function handleRegister(event) {
  try {
    if (event.is_registered) {
      const registrationId = await findActiveRegistrationId(event.id);
      if (!registrationId) {
        toast.error("Could not find that registration.");
        return;
      }
      await api.post(`/registrations/${registrationId}/cancel/`);
      toast.success("Registration cancelled.");
    } else {
      await api.post("/registrations/", { event_id: event.id });
      toast.success("You're registered! Check your email for confirmation.");
    }
    await loadEvent();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Something went wrong.");
  }
}

/** The cancel endpoint is keyed by registration id, which the event payload doesn't carry. */
async function findActiveRegistrationId(eventId) {
  const data = await api.get("/users/me/registrations/?status=registered");
  const match = (data.results || []).find((registration) => registration.event?.id === eventId);
  return match?.id || null;
}

async function handleSave(event) {
  try {
    if (event.is_saved) {
      await api.delete(`/events/${event.id}/save/`);
      toast.success("Removed from saved events.");
    } else {
      await api.post(`/events/${event.id}/save/`);
      toast.success("Saved for later.");
    }
    await loadEvent();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Something went wrong.");
  }
}

/**
 * "Similar events" is derived client-side from the event's own categories —
 * the API has no dedicated similarity endpoint.
 */
async function loadSimilarEvents(event) {
  const categorySlugs = event.categories.map((c) => c.slug);
  if (categorySlugs.length === 0) return;

  const query = new URLSearchParams({ upcoming: "true", page_size: "6" });
  categorySlugs.forEach((categorySlug) => query.append("category", categorySlug));

  try {
    const data = await api.get(`/events/?${query.toString()}`);
    const similar = toEventList(data).filter((candidate) => candidate.id !== event.id);
    if (similar.length === 0) return;
    qs("#similar-events-section").style.display = "block";
    renderEventGrid(qs("#similar-events-grid"), similar.slice(0, 3));
  } catch {
    // Similar events are a nice-to-have — fail silently if unavailable.
  }
}

async function loadEvent() {
  const event = await api.get(`/events/${slug}/`);
  renderEvent(event);
  return event;
}

async function init() {
  await renderHeader();
  renderFooter();

  if (!slug) {
    content.innerHTML = `<div class="empty-state">No event specified.</div>`;
    return;
  }

  currentUser = await getCurrentUser();

  try {
    const event = await loadEvent();
    loadSimilarEvents(event);
  } catch {
    content.innerHTML = `<div class="empty-state">This event could not be found.<br><a class="btn btn-primary" style="margin-top:16px;" href="/pages/event-listings.html">Browse events</a></div>`;
  }
}

init();
