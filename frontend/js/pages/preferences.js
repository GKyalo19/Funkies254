import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

let categories = [];
let schoolLevels = [];

// Mirrors UserPreference on the API: one school level, many categories, two toggles.
let preference = {
  school_level_id: null,
  preferred_category_ids: [],
  email_notifications: true,
  push_notifications: false,
};

function renderTags(container, options, isSelected, onToggle) {
  container.innerHTML = options
    .map(
      (opt) =>
        `<span class="tag ${isSelected(opt) ? "selected" : ""}" data-value="${escapeHtml(opt.id)}">${escapeHtml(opt.name)}</span>`
    )
    .join("");
  container.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => onToggle(tagEl.dataset.value));
  });
}

function renderAll() {
  // School level is single-select: clicking the active one clears it.
  renderTags(
    qs("#school-level-tags"),
    schoolLevels,
    (level) => level.id === preference.school_level_id,
    (value) => {
      preference.school_level_id = preference.school_level_id === value ? null : value;
      renderAll();
    }
  );

  renderTags(
    qs("#category-tags"),
    categories,
    (category) => preference.preferred_category_ids.includes(category.id),
    (value) => {
      preference.preferred_category_ids = preference.preferred_category_ids.includes(value)
        ? preference.preferred_category_ids.filter((id) => id !== value)
        : [...preference.preferred_category_ids, value];
      renderAll();
    }
  );

  qs("#email_notifications").checked = preference.email_notifications;
  qs("#push_notifications").checked = preference.push_notifications;
}

async function loadData() {
  const [categoriesResponse, levelsResponse, preferenceResponse] = await Promise.all([
    api.get("/categories/"),
    api.get("/school-levels/"),
    api.get("/preferences/me/"),
  ]);

  categories = categoriesResponse;
  schoolLevels = levelsResponse;
  preference = {
    school_level_id: preferenceResponse.school_level?.id || null,
    preferred_category_ids: (preferenceResponse.preferred_categories || []).map((c) => c.id),
    email_notifications: preferenceResponse.email_notifications ?? true,
    push_notifications: preferenceResponse.push_notifications ?? false,
  };
  renderAll();
}

async function handleSave(event) {
  event.preventDefault();
  const saveBtn = qs("#save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  try {
    await api.patch("/preferences/me/", {
      school_level_id: preference.school_level_id,
      preferred_category_ids: preference.preferred_category_ids,
      email_notifications: qs("#email_notifications").checked,
      push_notifications: qs("#push_notifications").checked,
    });
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

  try {
    await loadData();
  } catch (err) {
    toast.error("Could not load your preferences.");
    return;
  }

  qs("#preferences-form").addEventListener("submit", handleSave);
  qs("#discard-btn").addEventListener("click", loadData);
}

init();
