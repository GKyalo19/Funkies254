/** Renders a single event card — reused on the home feed, listings, and "similar events". */
import { escapeHtml, formatShortDate } from "../utils/dom.js";

const DEFAULT_COVER = "/assets/images/event-cover-default.jpg";

export function createEventCard(event) {
  // A real <a href> (not a click-listener on a <div>) so the card is a proper
  // link: keyboard-focusable, works with "open in new tab", crawlable, and
  // visible to accessibility tooling/screen readers.
  const card = document.createElement("a");
  card.className = "event-card";
  card.href = `/pages/event.html?slug=${encodeURIComponent(event.slug)}`;
  const cover = event.cover_image_url || DEFAULT_COVER;
  card.innerHTML = `
    <div class="cover">
      ${event.is_featured ? '<span class="badge">Featured</span>' : ""}
      <img src="${cover}" alt="${escapeHtml(event.title)}" loading="lazy" />
    </div>
    <div class="overlay"></div>
    <div class="body">
      <h3>${escapeHtml(event.title)}</h3>
      <p class="meta">${escapeHtml(event.organizer_name || event.location)}</p>
      <p class="meta">${formatShortDate(event.start_datetime)}</p>
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
