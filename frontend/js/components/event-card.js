/** Renders a single event card — reused on the home feed, listings, and "similar events". */
import { escapeHtml, formatShortDateRange } from "../utils/dom.js";
import { coverInnerHtml } from "../utils/media.js";

/**
 * Pulls plain events out of whatever the endpoint returned.
 *
 * `/events/` and `/users/me/saved-events/` are paginated, `/recommendations/feed/`
 * wraps each event in a `{score, reasons, event}` envelope, and some callers
 * already hold a plain array — this flattens all three into `Event[]`.
 */
export function toEventList(payload) {
  const items = Array.isArray(payload) ? payload : payload?.results || [];
  return items.map((item) => item?.event || item).filter(Boolean);
}

export function createEventCard(event) {
  // A real <a href> (not a click-listener on a <div>) so the card is a proper
  // link: keyboard-focusable, works with "open in new tab", crawlable, and
  // visible to accessibility tooling/screen readers.
  const card = document.createElement("a");
  card.className = "event-card";
  card.href = `/pages/event.html?slug=${encodeURIComponent(event.slug)}`;
  const venue = event.is_virtual
    ? "Virtual"
    : event.venue || event.location || event.institution?.name || "Venue TBC";
  card.innerHTML = `
    <div class="cover">
      ${event.is_virtual ? '<span class="badge">Virtual</span>' : ""}
      ${coverInnerHtml(event.cover_image_url, event.title)}
    </div>
    <div class="overlay"></div>
    <div class="body">
      <h3>${escapeHtml(event.title)}</h3>
      <p class="meta meta-row">
        <span>${escapeHtml(formatShortDateRange(event.start_time, event.end_time))}</span>
        <span>${escapeHtml(venue)}</span>
      </p>
    </div>
  `;
  return card;
}

/** Clears `container` and fills it with cards, or an empty-state message. */
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
    .map(
      () => `
      <div class="event-card">
        <div class="skeleton" style="position:absolute;inset:0;"></div>
      </div>`
    )
    .join("");
}
