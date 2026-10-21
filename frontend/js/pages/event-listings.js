import { renderFooter } from "../components/footer.js";
import { renderCardSkeletons, renderEventGrid, toEventList } from "../components/event-card.js";
import { renderHeader } from "../components/header.js";
import { api } from "../utils/api.js";
import { getCurrentUser } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const FORMAT_OPTIONS = [
  { value: "", label: "All" },
  { value: "in_person", label: "In person" },
  { value: "online", label: "Online" },
  { value: "hybrid", label: "Hybrid" },
];

const WHEN_OPTIONS = [
  { value: "", label: "All upcoming" },
  { value: "week", label: "This week" },
  { value: "month", label: "This month" },
  { value: "quarter", label: "Next 3 months" },
];

const COUNTRIES = ["Kenya", "Uganda", "Tanzania", "Rwanda", "Other"];

const urlParams = new URLSearchParams(window.location.search);
const state = {
  sections: urlParams.getAll("section"),
  category: urlParams.get("category") || "",
  school_level: urlParams.get("school_level") || "",
  format: urlParams.get("format") || "",
  when: urlParams.get("when") || "",
  country: urlParams.get("country") || "Kenya",
  near: urlParams.get("near") || "",
  radius_km: urlParams.get("radius_km") || "",
  free: urlParams.get("is_free") === "true",
  ordering: urlParams.get("ordering") || "",
  institution_slug: urlParams.get("institution_slug") || "",
  search: urlParams.get("search") || "",
  page: Number(urlParams.get("page")) || 1,
};

let sections = [];

function syncUrl() {
  const query = new URLSearchParams();
  state.sections.forEach((slug) => query.append("section", slug));
  ["category", "school_level", "format", "when", "near", "radius_km", "ordering", "institution_slug", "search"].forEach((key) => {
    if (state[key]) query.set(key, state[key]);
  });
  if (state.country && state.country !== "Kenya") query.set("country", state.country);
  if (state.free) query.set("is_free", "true");
  if (state.page > 1) query.set("page", state.page);
  const queryString = query.toString();
  window.history.replaceState({}, "", queryString ? `?${queryString}` : window.location.pathname);
}

function renderChipGroup(container, options, currentValue, onSelect) {
  if (!container) return;
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

function apply(patch) {
  Object.assign(state, patch);
  state.page = 1;
  syncUrl();
  renderFilters();
  loadEvents();
}

function visibleCategories() {
  const chosen = state.sections.length ? sections.filter((section) => state.sections.includes(section.slug)) : sections;
  return chosen.flatMap((section) =>
    (section.categories || []).map((category) => ({
      ...category,
      sectionName: section.name,
    }))
  );
}

function renderFilters() {
  const sectionMount = qs("#filter-section");
  sectionMount.innerHTML = sections
    .map(
      (section) =>
        `<label class="filter-check"><input type="checkbox" value="${escapeHtml(section.slug)}" ${state.sections.includes(section.slug) ? "checked" : ""}/> ${escapeHtml(section.name)}</label>`
    )
    .join("");
  sectionMount.querySelectorAll("input").forEach((input) => {
    input.addEventListener("change", () => {
      const selected = Array.from(sectionMount.querySelectorAll("input:checked")).map((box) => box.value);
      const keepLevel = selected.includes("high-school-events");
      apply({ sections: selected, school_level: keepLevel ? state.school_level : "" });
    });
  });

  const categories = visibleCategories();
  renderChipGroup(
    qs("#filter-category"),
    [{ value: "", label: "All" }, ...categories.map((category) => ({ value: category.slug, label: category.name }))],
    state.category,
    (value) => apply({ category: value })
  );

  const schoolGroup = qs("#school-level-group");
  const showSchool = state.sections.includes("high-school-events");
  schoolGroup.style.display = showSchool ? "" : "none";
  renderChipGroup(
    qs("#filter-school-level"),
    [
      { value: "", label: "All" },
      { value: "junior-secondary", label: "Junior Secondary" },
      { value: "senior-secondary", label: "Senior Secondary" },
    ],
    state.school_level,
    (value) => apply({ school_level: value })
  );
  renderChipGroup(qs("#filter-format"), FORMAT_OPTIONS, state.format, (value) => apply({ format: value }));
  renderChipGroup(qs("#filter-when"), WHEN_OPTIONS, state.when, (value) => apply({ when: value }));
  renderChipGroup(
    qs("#filter-sort"),
    [
      { value: "", label: state.ordering === "-popularity_score" ? "Most popular" : "Recommended" },
      { value: "-popularity_score", label: "Most popular" },
      { value: "start_time", label: "Soonest" },
    ],
    state.ordering,
    (value) => apply({ ordering: value })
  );
}

function dateRange() {
  const now = new Date();
  const start = now.toISOString();
  if (state.when === "week") {
    const end = new Date(now.getTime() + 7 * 86400000);
    return { start_after: start, start_before: end.toISOString() };
  }
  if (state.when === "month") {
    const end = new Date(now.getFullYear(), now.getMonth() + 1, now.getDate());
    return { start_after: start, start_before: end.toISOString() };
  }
  if (state.when === "quarter") {
    const end = new Date(now.getTime() + 90 * 86400000);
    return { start_after: start, start_before: end.toISOString() };
  }
  return {};
}

function buildQueryString() {
  const query = new URLSearchParams();
  state.sections.forEach((slug) => query.append("section", slug));
  if (state.category) query.append("category", state.category);
  if (state.school_level) query.set("school_level", state.school_level);
  if (state.format) query.set("format", state.format);
  if (state.country) query.set("country", state.country);
  if (state.free) query.set("is_free", "true");
  if (state.near) {
    query.set("near", state.near);
    query.set("radius_km", state.radius_km || "25");
  }
  if (state.ordering) query.set("ordering", state.ordering);
  if (state.institution_slug) query.set("institution_slug", state.institution_slug);
  if (state.search) query.set("search", state.search);
  const range = dateRange();
  if (range.start_after) query.set("start_after", range.start_after);
  if (range.start_before) query.set("start_before", range.start_before);
  query.set("page", state.page);
  return query.toString();
}

async function loadEvents() {
  const grid = qs("#listings-grid");
  renderCardSkeletons(grid);
  try {
    const data = await api.get(`/events/?${buildQueryString()}`);
    const events = toEventList(data);
    if (state.search && events.some((event) => event.is_past)) {
      grid.innerHTML = "";
      const upcoming = events.filter((event) => !event.is_past);
      const past = events.filter((event) => event.is_past);
      const upcomingMount = document.createElement("div");
      upcomingMount.className = "event-grid";
      grid.appendChild(upcomingMount);
      renderEventGrid(upcomingMount, upcoming, "No upcoming events match that search.");
      if (past.length) {
        const heading = document.createElement("h2");
        heading.textContent = "Past events";
        heading.style.margin = "28px 0 12px";
        grid.appendChild(heading);
        const pastMount = document.createElement("div");
        pastMount.className = "event-grid";
        grid.appendChild(pastMount);
        renderEventGrid(pastMount, past);
      }
    } else {
      renderEventGrid(grid, events, "No events match those filters yet.");
    }
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

async function init() {
  const user = await getCurrentUser();
  if (!state.ordering) state.ordering = user ? "" : "-popularity_score";
  await renderHeader(state.search);
  renderFooter();
  if (state.search) qs("#listings-heading").textContent = `Results for "${state.search}"`;
  else if (state.sections.length === 1) {
    const match = {
      "college-events": "College Events",
      "high-school-events": "High School Events",
      "college-app-resources": "College Application Resources",
    }[state.sections[0]];
    if (match) qs("#listings-heading").textContent = match;
  }

  sections = await api.get("/sections/").catch(() => []);
  const country = qs("#filter-country");
  country.innerHTML = COUNTRIES.map(
    (name) => `<option value="${name}" ${name === state.country ? "selected" : ""}>${name}</option>`
  ).join("");
  country.addEventListener("change", () => apply({ country: country.value }));
  qs("#filter-free").checked = state.free;
  qs("#filter-free").addEventListener("change", (event) => apply({ free: event.target.checked }));
  qs("#near-me").addEventListener("click", () => {
    if (!navigator.geolocation) {
      toast.error("Location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const near = `${position.coords.latitude.toFixed(2)},${position.coords.longitude.toFixed(2)}`;
        apply({ near, radius_km: "25" });
      },
      () => toast.error("Location permission was denied. Showing events in your selected country.")
    );
  });
  qs("#filter-clear").addEventListener("click", () => {
    state.sections = [];
    state.category = "";
    state.school_level = "";
    state.format = "";
    state.when = "";
    state.country = "Kenya";
    state.near = "";
    state.radius_km = "";
    state.free = false;
    state.ordering = user ? "" : "-popularity_score";
    state.institution_slug = "";
    state.search = "";
    state.page = 1;
    qs("#filter-free").checked = false;
    country.value = "Kenya";
    syncUrl();
    renderFilters();
    loadEvents();
  });
  renderFilters();
  await loadEvents();
}

init();
