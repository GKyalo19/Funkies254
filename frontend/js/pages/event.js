import { renderFooter } from "../components/footer.js";
import { renderEventGrid } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { getCurrentUser, initials } from "../utils/auth.js";
import { escapeHtml, formatDate, formatFee, formatTimeRange, getQueryParam, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const slug = getQueryParam("slug");
const content = qs("#event-content");

function organizerRowHtml(organizer) {
  return `
    <div class="organizer-row">
      <div class="avatar">
        ${organizer.logo_url ? `<img src="${organizer.logo_url}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : initials({ full_name: organizer.name })}
      </div>
      <div class="info">
        <h4>by ${escapeHtml(organizer.name)}</h4>
        <p class="stats">
          ${organizer.followers_count.toLocaleString()} followers &middot; ${organizer.years_hosting}y hosting
        </p>
      </div>
      <div class="actions">
        ${organizer.contact_email ? `<a class="btn btn-secondary" href="mailto:${organizer.contact_email}">Contact</a>` : ""}
        <button class="btn ${organizer.is_following ? "btn-secondary" : "btn-gold"}" id="follow-btn">
          ${organizer.is_following ? "Following" : "Follow"}
        </button>
      </div>
    </div>
  `;
}

function registrationCardHtml(event) {
  if (event.external_registration_url) {
    return `
      <div class="registration-card">
        <h4>${escapeHtml(event.venue_name)}</h4>
        <div class="fee-display">${formatFee(event.registration_fee)}</div>
        <a class="btn btn-gold btn-block" href="${event.external_registration_url}" target="_blank" rel="noopener">Register externally</a>
      </div>
    `;
  }

  const full = event.spots_left !== null && event.spots_left <= 0;
  const label = event.is_registered ? "Cancel registration" : full ? "Fully booked" : "Register";
  const disabled = full && !event.is_registered ? "disabled" : "";

  return `
    <div class="registration-card">
      <h4>${escapeHtml(event.venue_name)}</h4>
      <div class="fee-display">${formatFee(event.registration_fee)}</div>
      ${event.spots_left !== null ? `<p class="spots">${event.spots_left} spot${event.spots_left === 1 ? "" : "s"} left</p>` : ""}
      <button class="btn btn-block ${event.is_registered ? "btn-danger" : "btn-gold"}" id="register-btn" ${disabled}>
        ${label}
      </button>
    </div>
  `;
}

function renderEvent(event) {
  const description = escapeHtml(event.description);
  const isLong = description.length > 260;
  const shortDescription = isLong ? `${description.slice(0, 260)}&hellip;` : description;

  content.innerHTML = `
    <div class="event-hero">
      ${event.cover_image_url ? `<img src="${escapeHtml(event.cover_image_url)}" alt="${escapeHtml(event.title)}" />` : `<img src="/assets/images/event-cover-default.jpg" alt="" />`}
    </div>

    ${organizerRowHtml(event.organizer)}

    <div class="event-detail-layout">
      <div>
        <div class="categories" style="margin-bottom:12px;">
          ${event.categories.map((c) => `<span class="pill">${escapeHtml(c.name)}</span>`).join("")}
        </div>
        <h1 class="event-title">${escapeHtml(event.title)}</h1>

        <div class="event-info-list" style="margin:24px 0;">
          <div class="info-row">
            <div class="icon"><img src="/assets/icons/icon-location.svg" alt="" /></div>
            <div>
              <strong>${escapeHtml(event.venue_name)}</strong>
              <p style="margin:2px 0 0;color:var(--color-text-muted);">${escapeHtml(event.address || event.location)}</p>
            </div>
          </div>
          <div class="info-row">
            <div class="icon"><img src="/assets/icons/icon-calendar.svg" alt="" /></div>
            <div>
              <strong>${formatDate(event.start_datetime)}</strong>
              <p style="margin:2px 0 0;color:var(--color-text-muted);">${formatTimeRange(event.start_datetime, event.end_datetime)}</p>
            </div>
          </div>
        </div>

        <div class="event-body-text">
          <h3>Overview</h3>
          <p id="event-description">${shortDescription}</p>
          ${isLong ? `<a class="read-more-link" id="read-more-btn" href="#" data-full="${description}" data-short="${shortDescription}">Read more</a>` : ""}

          <h3>Location</h3>
          <p>${escapeHtml(event.venue_name)} &middot; ${escapeHtml(event.address || event.location)}</p>
        </div>
      </div>

      <div>${registrationCardHtml(event)}</div>
    </div>
  `;

  const followBtn = qs("#follow-btn", content);
  if (followBtn) {
    followBtn.addEventListener("click", () => handleFollow(event.organizer));
  }

  const registerBtn = qs("#register-btn", content);
  if (registerBtn) {
    registerBtn.addEventListener("click", () => handleRegister(event));
  }

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

async function handleFollow(organizer) {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = "/pages/login.html";
    return;
  }
  try {
    if (organizer.is_following) {
      await api.delete(`/organizers/${organizer.slug}/follow/`);
      toast.success(`Unfollowed ${organizer.name}.`);
    } else {
      await api.post(`/organizers/${organizer.slug}/follow/`);
      toast.success(`Now following ${organizer.name}.`);
    }
    await loadEvent();
  } catch (err) {
    toast.error(err.message);
  }
}

async function handleRegister(event) {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = "/pages/login.html";
    return;
  }
  try {
    if (event.is_registered) {
      const registrations = await api.get("/registrations/");
      const mine = registrations.results.find((r) => r.event.slug === event.slug);
      if (mine) await api.delete(`/registrations/${mine.id}/`);
      toast.success("Registration cancelled.");
    } else {
      await api.post("/registrations/", { event_slug: event.slug });
      toast.success("You're registered! 🎉");
    }
    await loadEvent();
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Something went wrong.");
  }
}

async function loadSimilarEvents() {
  try {
    const similar = await api.get(`/events/${slug}/similar/`);
    if (similar.length > 0) {
      qs("#similar-events-section").style.display = "block";
      renderEventGrid(qs("#similar-events-grid"), similar);
    }
  } catch {
    // Similar events are a nice-to-have — fail silently if unavailable.
  }
}

async function loadEvent() {
  try {
    const event = await api.get(`/events/${slug}/`);
    renderEvent(event);
  } catch (err) {
    content.innerHTML = `<div class="empty-state">This event could not be found.<br><a class="btn btn-primary" style="margin-top:16px;" href="/pages/event-listings.html">Browse events</a></div>`;
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  if (!slug) {
    content.innerHTML = `<div class="empty-state">No event specified.</div>`;
    return;
  }

  await loadEvent();
  loadSimilarEvents();
}

init();
