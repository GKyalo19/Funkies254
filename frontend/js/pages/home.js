import { renderFooter } from "../components/footer.js";
import { renderEventGrid, renderCardSkeletons } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { getCurrentUser } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

async function renderHeroActions() {
  const user = await getCurrentUser();
  const mount = qs("#hero-actions");
  if (user) {
    mount.innerHTML = `<p class="hero-welcome">Welcome back, ${escapeHtml(user.first_name || user.full_name)} 👋</p>`;
  } else {
    mount.innerHTML = `<a href="/pages/login.html">Log In / Register</a>`;
  }
}

function wireHeroSearch() {
  const form = qs("#hero-search-form");
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const query = new FormData(event.target).get("q") || "";
    window.location.href = `/pages/event-listings.html?search=${encodeURIComponent(query)}`;
  });
}

async function renderCategoryChips() {
  const mount = qs("#category-chips");
  try {
    const categories = await api.get("/events/categories/");
    mount.innerHTML = categories
      .map(
        (category) =>
          `<a class="category-chip" href="/pages/event-listings.html?category=${encodeURIComponent(category.slug)}">${escapeHtml(category.name)}</a>`
      )
      .join("");
  } catch (err) {
    mount.innerHTML = "";
  }
}

async function renderFeed() {
  const grid = qs("#feed-grid");
  renderCardSkeletons(grid);
  try {
    const feed = await api.get("/recommendations/feed/?limit=9");
    renderEventGrid(grid, feed.results, "No events yet — check back soon!");
  } catch (err) {
    toast.error(err.message);
    grid.innerHTML = "";
  }
}

async function init() {
  await renderHeader();
  renderFooter();
  wireHeroSearch();
  renderHeroActions();
  renderCategoryChips();
  renderFeed();
}

init();
