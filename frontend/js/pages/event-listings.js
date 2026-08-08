import { renderFooter } from "../components/footer.js";
import { renderEventGrid, renderCardSkeletons } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const EDUCATION_LEVELS = [
  { value: "", label: "All" },
  { value: "high_school", label: "High School" },
  { value: "college", label: "College" },
];

const FEE_OPTIONS = [
  { value: "", label: "All" },
  { value: "free", label: "Free" },
  { value: "paid", label: "Paid" },
];

const urlParams = new URLSearchParams(window.location.search);
const state = {
  category: urlParams.get("category") || "",
  location: urlParams.get("location") || "",
  education_level: urlParams.get("education_level") || "",
  fee: urlParams.get("fee") || "",
  search: urlParams.get("search") || "",
  page: Number(urlParams.get("page")) || 1,
};

let categoryOptions = [{ value: "", label: "All" }];

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

function refreshCategoryChips() {
  renderChipGroup(qs("#filter-category"), categoryOptions, state.category, selectCategory);
}

function refreshEducationChips() {
  renderChipGroup(qs("#filter-education"), EDUCATION_LEVELS, state.education_level, selectEducationLevel);
}

function refreshFeeChips() {
  renderChipGroup(qs("#filter-fee"), FEE_OPTIONS, state.fee, selectFee);
}

function selectCategory(value) {
  state.category = value;
  state.page = 1;
  syncUrl();
  refreshCategoryChips();
  loadEvents();
}

function selectEducationLevel(value) {
  state.education_level = value;
  state.page = 1;
  syncUrl();
  refreshEducationChips();
  loadEvents();
}

function selectFee(value) {
  state.fee = value;
  state.page = 1;
  syncUrl();
  refreshFeeChips();
  loadEvents();
}

async function loadCategoryFilter() {
  try {
    const categories = await api.get("/events/categories/");
    categoryOptions = [{ value: "", label: "All" }, ...categories.map((c) => ({ value: c.slug, label: c.name }))];
  } catch {
    categoryOptions = [{ value: "", label: "All" }];
  }
  refreshCategoryChips();
}

function buildQueryString() {
  const query = new URLSearchParams();
  if (state.category) query.set("category", state.category);
  if (state.location) query.set("location", state.location);
  if (state.education_level) query.set("education_level", state.education_level);
  if (state.fee) query.set("fee", state.fee);
  if (state.search) query.set("search", state.search);
  query.set("page", state.page);
  return query.toString();
}

async function loadEvents() {
  const grid = qs("#listings-grid");
  renderCardSkeletons(grid);

  try {
    const data = await api.get(`/events/?${buildQueryString()}`);
    renderEventGrid(grid, data.results, "No events match those filters yet.");
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

function setupStaticFilters() {
  refreshEducationChips();
  refreshFeeChips();

  const locationInput = qs("#filter-location");
  locationInput.value = state.location;
  let debounceTimer;
  locationInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      state.location = locationInput.value.trim();
      state.page = 1;
      syncUrl();
      loadEvents();
    }, 400);
  });

  qs("#filter-clear").addEventListener("click", () => {
    state.category = "";
    state.location = "";
    state.education_level = "";
    state.fee = "";
    state.page = 1;
    locationInput.value = "";
    syncUrl();
    refreshCategoryChips();
    refreshEducationChips();
    refreshFeeChips();
    loadEvents();
  });
}

async function init() {
  await renderHeader(state.search);
  renderFooter();

  if (state.search) {
    qs("#listings-heading").textContent = `Results for "${state.search}"`;
  }

  await loadCategoryFilter();
  setupStaticFilters();
  await loadEvents();
}

init();
