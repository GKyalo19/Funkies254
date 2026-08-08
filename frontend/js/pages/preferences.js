import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const EDUCATION_LEVELS = [
  { value: "high_school", label: "High School" },
  { value: "college", label: "College" },
];

const DAYS_AHEAD_OPTIONS = [7, 14, 30, 60, 90];

let categories = [];
let preference = null; // current saved state (categories: [ids], education_levels: [strings], preferred_locations: [strings], max_days_ahead: number)

function renderMultiTags(container, options, selectedValues, onToggle) {
  container.innerHTML = options
    .map(
      (opt) =>
        `<span class="tag ${selectedValues.includes(opt.value) ? "selected" : ""}" data-value="${escapeHtml(String(opt.value))}">${escapeHtml(opt.label)}</span>`
    )
    .join("");
  container.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => onToggle(tagEl.dataset.value));
  });
}

function renderSingleSelectTags(container, options, selectedValue, onSelect) {
  container.innerHTML = options
    .map(
      (opt) =>
        `<span class="tag ${Number(opt) === Number(selectedValue) ? "selected" : ""}" data-value="${opt}">${opt} days</span>`
    )
    .join("");
  container.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => onSelect(Number(tagEl.dataset.value)));
  });
}

function renderLocationTags() {
  const container = qs("#location-tags");
  if (preference.preferred_locations.length === 0) {
    container.innerHTML = `<span style="color:var(--color-text-muted);font-size:13px;">No locations added yet — showing events everywhere.</span>`;
    return;
  }
  container.innerHTML = preference.preferred_locations
    .map((loc) => `<span class="tag selected" data-value="${escapeHtml(loc)}">${escapeHtml(loc)} &times;</span>`)
    .join("");
  container.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => {
      preference.preferred_locations = preference.preferred_locations.filter((l) => l !== tagEl.dataset.value);
      renderLocationTags();
    });
  });
}

function renderAll() {
  renderMultiTags(qs("#education-tags"), EDUCATION_LEVELS, preference.education_levels, (value) => {
    preference.education_levels = preference.education_levels.includes(value)
      ? preference.education_levels.filter((v) => v !== value)
      : [...preference.education_levels, value];
    renderAll();
  });

  const categoryOptions = categories.map((c) => ({ value: c.id, label: c.name }));
  renderMultiTags(qs("#category-tags"), categoryOptions, preference.categories, (value) => {
    const id = Number(value);
    preference.categories = preference.categories.includes(id)
      ? preference.categories.filter((v) => v !== id)
      : [...preference.categories, id];
    renderAll();
  });

  renderLocationTags();

  renderSingleSelectTags(qs("#days-ahead-tags"), DAYS_AHEAD_OPTIONS, preference.max_days_ahead, (value) => {
    preference.max_days_ahead = value;
    renderAll();
  });
}

async function loadData() {
  const [categoriesResponse, preferenceResponse] = await Promise.all([
    api.get("/events/categories/"),
    api.get("/preferences/me/"),
  ]);
  categories = categoriesResponse;
  preference = {
    categories: preferenceResponse.categories || [],
    education_levels: preferenceResponse.education_levels || [],
    preferred_locations: preferenceResponse.preferred_locations || [],
    max_days_ahead: preferenceResponse.max_days_ahead || 30,
  };
  renderAll();
}

async function handleSave(event) {
  event.preventDefault();
  const saveBtn = qs("#save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  try {
    await api.patch("/preferences/me/", preference);
    toast.success("Preferences saved — your feed will now reflect these.");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not save preferences.");
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Changes";
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  await loadData();

  qs("#preferences-form").addEventListener("submit", handleSave);
  qs("#discard-btn").addEventListener("click", loadData);

  const locationInput = qs("#new-location-input");
  locationInput.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const value = locationInput.value.trim();
    if (value && !preference.preferred_locations.includes(value)) {
      preference.preferred_locations.push(value);
      renderLocationTags();
    }
    locationInput.value = "";
  });
}

init();
