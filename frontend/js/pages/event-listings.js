import { renderFooter } from "../components/footer.js";
import { renderEventGrid, renderCardSkeletons, toEventList } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

// Mirrors the `is_virtual` filter on the API (backend/apps/events/filters.py).
const FORMAT_OPTIONS = [
  { value: "", label: "All" },
  { value: "false", label: "In person" },
  { value: "true", label: "Virtual" },
];

const WHEN_OPTIONS = [
  { value: "true", label: "Upcoming" },
  { value: "", label: "All dates" },
];

const urlParams = new URLSearchParams(window.location.search);
const state = {
  category: urlParams.get("category") || "",
  school_level: urlParams.get("school_level") || "",
  is_virtual: urlParams.get("is_virtual") || "",
  upcoming: urlParams.get("upcoming") ?? "true",
  institution_slug: urlParams.get("institution_slug") || "",
  search: urlParams.get("search") || "",
  page: Number(urlParams.get("page")) || 1,
};

let categoryOptions = [{ value: "", label: "All" }];
let schoolLevelOptions = [{ value: "", label: "All" }];

function syncUrl() {
  const query = new URLSearchParams();
  Object.entries(state).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  const queryString = query.toString();
  window.history.replaceState({}, "", queryString ? `?${queryString}` : window.location.pathname);
}

function renderChipGroup(container, options, currentValue, onSelect) {
  container.innerHTML = options
    .map(
      (option) =>
        `<span class="filter-tag ${option.value === currentValue ? "active" : ""}" data-value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</span>`
    )
    .join("");
  container.querySelectorAll(".filter-tag").forEach((tag) => {
    tag.addEventListener("click", () => onSelect(tag.dataset.value));
  });
}

/** Every filter change resets to page 1 and reloads. */
function applyFilter(key, value) {
  state[key] = value;
  state.page = 1;
  syncUrl();
  refreshAllChips();
  loadEvents();
}

function refreshAllChips() {
  renderChipGroup(qs("#filter-category"), categoryOptions, state.category, (v) => applyFilter("category", v));
  renderChipGroup(qs("#filter-school-level"), schoolLevelOptions, state.school_level, (v) => applyFilter("school_level", v));
  renderChipGroup(qs("#filter-format"), FORMAT_OPTIONS, state.is_virtual, (v) => applyFilter("is_virtual", v));
  renderChipGroup(qs("#filter-when"), WHEN_OPTIONS, state.upcoming, (v) => applyFilter("upcoming", v));
}

async function loadFilterOptions() {
  const [categories, schoolLevels] = await Promise.all([
    api.get("/categories/").catch(() => []),
    api.get("/school-levels/").catch(() => []),
  ]);
  categoryOptions = [{ value: "", label: "All" }, ...categories.map((c) => ({ value: c.slug, label: c.name }))];
  schoolLevelOptions = [{ value: "", label: "All" }, ...schoolLevels.map((l) => ({ value: l.slug, label: l.name }))];
  refreshAllChips();
}

function buildQueryString() {
  const query = new URLSearchParams();
  if (state.category) query.set("category", state.category);
  if (state.school_level) query.set("school_level", state.school_level);
  if (state.is_virtual) query.set("is_virtual", state.is_virtual);
  if (state.upcoming) query.set("upcoming", state.upcoming);
  if (state.institution_slug) query.set("institution_slug", state.institution_slug);
  if (state.search) query.set("search", state.search);
  query.set("page", state.page);
  return query.toString();
}

async function loadEvents() {
  const grid = qs("#listings-grid");
  renderCardSkeletons(grid);

  try {
    const data = await api.get(`/events/?${buildQueryString()}`);
    renderEventGrid(grid, toEventList(data), "No events match those filters yet.");
    qs("#results-count").textContent = `${data.count} event${data.count === 1 ? "" : "s"} found`;
    renderPagination(data);
  } catch (err) {
    toast.error(err.message);
    grid.innerHTML = "";
  }
}

function renderPagination(data) {
  const container = qs("#pagination-controls");
  container.innerHTML = "";
  if (!data.previous && !data.next) return;

  if (data.previous) {
    const prevBtn = document.createElement("button");
    prevBtn.className = "btn btn-secondary btn-sm";
    prevBtn.textContent = "← Previous";
    prevBtn.addEventListener("click", () => {
      state.page = Math.max(1, state.page - 1);
      syncUrl();
      loadEvents();
    });
    container.appendChild(prevBtn);
  }

  if (data.next) {
    const nextBtn = document.createElement("button");
    nextBtn.className = "btn btn-secondary btn-sm";
    nextBtn.textContent = "Next →";
    nextBtn.addEventListener("click", () => {
      state.page += 1;
      syncUrl();
      loadEvents();
    });
    container.appendChild(nextBtn);
  }
}

function wireClearButton() {
  qs("#filter-clear").addEventListener("click", () => {
    state.category = "";
    state.school_level = "";
    state.is_virtual = "";
    state.upcoming = "true";
    state.institution_slug = "";
    state.search = "";
    state.page = 1;
    syncUrl();
    refreshAllChips();
    loadEvents();
  });
}

async function init() {
  await renderHeader(state.search);
  renderFooter();

  if (state.search) {
    qs("#listings-heading").textContent = `Results for "${state.search}"`;
  }

  wireClearButton();
  await loadFilterOptions();
  await loadEvents();
}

init();
