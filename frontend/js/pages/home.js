import { renderFooter } from "../components/footer.js";
import { renderCardSkeletons, renderEventGrid, toEventList } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { getCurrentUser } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";

const SECTIONS = [
  { slug: "college-events", title: "College Events" },
  { slug: "high-school-events", title: "High School Events" },
  { slug: "college-app-resources", title: "College Application Resources", placeholder: true },
];

function sectionBlock(section) {
  return `
    <section class="page-section container" id="section-${section.slug}">
      <div class="section-heading">
        <h2><a href="/pages/event-listings.html?section=${section.slug}">${escapeHtml(section.title)}</a></h2>
        <a href="/pages/event-listings.html?section=${section.slug}">See all</a>
      </div>
      <p class="section-note" hidden></p>
      <div class="event-row" data-slug="${section.slug}"></div>
    </section>
  `;
}

async function renderHero() {
  const user = await getCurrentUser();
  const mount = qs("#hero-actions");
  const heading = qs("#popular-heading");
  if (user) {
    mount.innerHTML = "";
    if (heading) heading.textContent = "Recommended for You";
  } else {
    mount.innerHTML = `<a class="btn btn-primary" href="/pages/login.html">Log in / Register</a>`;
    if (heading) heading.textContent = "Popular Events";
  }
  return user;
}

async function renderPopular(user) {
  const row = qs("#popular-row");
  renderCardSkeletons(row, 4);
  const feed = await api.get("/recommendations/feed/?limit=10");
  row.className = "event-row";
  renderEventGrid(row, toEventList(feed).slice(0, 10), "No events yet — check back soon!");
  return user;
}

async function renderSection(section, user) {
  const row = document.querySelector(`[data-slug="${section.slug}"]`);
  const note = row.parentElement.querySelector(".section-note");
  if (section.placeholder) {
    row.innerHTML = `
      <div class="card-panel coming-soon-card">
        <img src="/assets/images/under-construction.gif" alt="Under construction" width="180" />
        <p>Coming soon</p>
      </div>
    `;
    return;
  }
  renderCardSkeletons(row, 3);
  const params = new URLSearchParams({
    section: section.slug,
    ordering: "-popularity_score",
    page_size: "6",
  });
  const preferenceCategories = user?.preference_categories || [];
  preferenceCategories.forEach((slug) => params.append("category", slug));
  let events = [];
  try {
    events = toEventList(await api.get(`/events/?${params.toString()}`));
  } catch {
    events = [];
  }
  if (user && preferenceCategories.length && events.length === 0) {
    const fallback = new URLSearchParams({
      section: section.slug,
      ordering: "-popularity_score",
      page_size: "6",
    });
    events = toEventList(await api.get(`/events/?${fallback.toString()}`));
    if (events.length) {
      note.hidden = false;
      note.textContent = "Nothing matches your preferences yet — here's what's popular.";
    }
  }
  row.className = "event-row";
  renderEventGrid(row, events, "No upcoming events in this section yet.");
}

async function init() {
  const search = qs("#hero-search-form");
  if (search) {
    search.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = new FormData(event.target).get("q") || "";
      window.location.href = `/pages/event-listings.html?search=${encodeURIComponent(query)}`;
    });
  }
  qs("#home-sections").innerHTML = SECTIONS.map(sectionBlock).join("");
  await renderHeader();
  renderFooter();
  const user = await renderHero();
  if (user) {
    try {
      const prefs = await api.get("/preferences/me/");
      user.preference_categories = (prefs.preferred_categories || []).map((category) => category.slug);
    } catch {
      user.preference_categories = [];
    }
  }
  await renderPopular(user);
  for (const section of SECTIONS) {
    await renderSection(section, user);
  }
}

init();
