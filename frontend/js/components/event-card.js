/** Event card used on the homepage, listings and saved events. */
import { api, ApiError } from "../utils/api.js";
import { getCurrentUser } from "../utils/auth.js";
import { escapeHtml, formatCardDate } from "../utils/dom.js";
import { coverInnerHtml } from "../utils/media.js";
import { toast } from "../utils/toast.js";

export function toEventList(payload) {
  const items = Array.isArray(payload) ? payload : payload?.results || [];
  return items.map((item) => item?.event || item).filter(Boolean);
}

function placeLabel(event) {
  if (event.format === "online" || event.is_virtual) return "Online";
  return event.venue || event.location || "Venue TBC";
}

export function createEventCard(event) {
  const card = document.createElement("article");
  card.className = "event-card";
  const category = event.categories?.[0];
  const cover = event.cover_image_url
    ? coverInnerHtml(event.cover_image_url, event.title)
    : category?.icon_url
      ? `<img class="cover-fallback" src="${escapeHtml(category.icon_url)}" alt="" />`
      : coverInnerHtml(null, event.title);
  const free = event.is_free === false ? "" : `<span class="tag">Free</span>`;
  const saved = Boolean(event.is_saved);

  card.innerHTML = `
    <a class="event-card-link" href="/pages/event.html?slug=${encodeURIComponent(event.slug)}">
      <div class="cover">
        ${event.is_past ? '<span class="badge badge-ended">Ended</span>' : ""}
        ${cover}
      </div>
      <div class="body">
        <h3>${escapeHtml(event.title)}</h3>
        <p class="meta">${escapeHtml(event.institution?.name || "Organiser TBC")}</p>
        <p class="meta">${escapeHtml(formatCardDate(event.start_time))}</p>
        <p class="meta">${escapeHtml(placeLabel(event))}</p>
        <p class="tag-row">
          ${category ? `<span class="tag">${escapeHtml(category.name)}</span>` : ""}
          ${free}
        </p>
      </div>
    </a>
    <button type="button" class="bookmark-btn ${saved ? "is-saved" : ""}" data-event-id="${escapeHtml(event.id)}" aria-label="${saved ? "Unsave event" : "Save event"}" aria-pressed="${saved}">
      <img src="${saved ? "/assets/icons/icon-bookmark-filled.svg" : "/assets/icons/icon-bookmark.svg"}" alt="" />
    </button>
    <button type="button" class="btn btn-gold btn-sm register-out">Register on organiser's site</button>
  `;

  const bookmark = card.querySelector(".bookmark-btn");
  bookmark.addEventListener("click", (click) => {
    click.preventDefault();
    click.stopPropagation();
    toggleSave(event, bookmark);
  });

  const register = card.querySelector(".register-out");
  register.addEventListener("click", (click) => {
    click.preventDefault();
    click.stopPropagation();
    openRegistration(event);
  });
  return card;
}

async function toggleSave(event, button) {
  const user = await getCurrentUser();
  if (!user) {
    const next = `${window.location.pathname}${window.location.search}`;
    window.location.href = `/pages/login.html?next=${encodeURIComponent(next)}&save=${encodeURIComponent(event.id)}`;
    return;
  }
  const wasSaved = button.classList.contains("is-saved");
  setBookmark(button, !wasSaved);
  try {
    if (wasSaved) await api.delete(`/events/${event.id}/save/`);
    else await api.post(`/events/${event.id}/save/`, {});
    event.is_saved = !wasSaved;
    if (wasSaved) {
      toast.success("Removed from saved events.", {
        action: {
          label: "Undo",
          onClick: async () => {
            try {
              await api.post(`/events/${event.id}/save/`, {});
              setBookmark(button, true);
              event.is_saved = true;
            } catch (undoErr) {
              toast.error(undoErr instanceof ApiError ? undoErr.message : "Couldn't restore that save.");
            }
          },
        },
      });
    }
  } catch (err) {
    setBookmark(button, wasSaved);
    toast.error(err instanceof ApiError ? err.message : "Couldn't save — try again");
  }
}

function setBookmark(button, saved) {
  const eventId = button.dataset.eventId;
  const buttons = eventId
    ? document.querySelectorAll(`.bookmark-btn[data-event-id="${CSS.escape(eventId)}"]`)
    : [button];
  buttons.forEach((target) => {
    target.classList.toggle("is-saved", saved);
    target.setAttribute("aria-pressed", saved ? "true" : "false");
    target.setAttribute("aria-label", saved ? "Unsave event" : "Save event");
    const img = target.querySelector("img");
    if (img) img.src = saved ? "/assets/icons/icon-bookmark-filled.svg" : "/assets/icons/icon-bookmark.svg";
  });
}

export async function openRegistration(event) {
  if (!event.registration_link) {
    toast.error("This event does not have a registration link yet.");
    return;
  }
  try {
    await api.post(`/events/${event.id}/click-out/`, {});
  } catch {
    // Still send the visitor to the organiser if the click could not be recorded.
  }
  window.open(event.registration_link, "_blank", "noopener");
}

export function renderEventGrid(container, events, emptyMessage = "No events found. Check back soon!") {
  container.innerHTML = "";
  if (!events || events.length === 0) {
    container.innerHTML = `<div class="empty-state">${escapeHtml(emptyMessage)}</div>`;
    return;
  }
  const fragment = document.createDocumentFragment();
  events.forEach((event) => fragment.appendChild(createEventCard(event)));
  container.appendChild(fragment);
}

export function renderCardSkeletons(container, count = 6) {
  container.innerHTML = Array.from({ length: count })
    .map(() => `<div class="event-card"><div class="skeleton" style="position:absolute;inset:0;"></div></div>`)
    .join("");
}
