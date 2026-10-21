import { renderFooter } from "../components/footer.js";
import { renderEventGrid } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { qs } from "../utils/dom.js";

async function init() {
  const user = await requireAuth();
  if (!user) return;
  await renderHeader();
  renderFooter();
  const data = await api.get("/users/me/saved-events/");
  const events = (data.results || []).map((row) => ({ ...row.event, is_saved: true }));
  const upcoming = events.filter((event) => !event.is_past).sort((a, b) => a.start_time.localeCompare(b.start_time));
  const past = events.filter((event) => event.is_past).sort((a, b) => b.start_time.localeCompare(a.start_time));
  const upcomingMount = qs("#saved-upcoming");
  if (!upcoming.length && !past.length) {
    upcomingMount.innerHTML = `No saved events yet. <a href="/pages/event-listings.html">Browse all events</a>`;
    return;
  }
  renderEventGrid(upcomingMount, upcoming, "No upcoming saved events.");
  const pastMount = qs("#saved-past");
  renderEventGrid(pastMount, past, "No past saved events.");
  qs("#toggle-past").addEventListener("click", () => {
    const hidden = pastMount.hidden;
    pastMount.hidden = !hidden;
    qs("#toggle-past").textContent = hidden ? "Hide past events" : "Show past events";
  });
}

init();
