import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache, initials, requireAuth } from "../utils/auth.js";
import { applyFieldErrors, attachPasswordToggle, escapeHtml, getQueryParam, qs } from "../utils/dom.js";
import { avatarInnerHtml } from "../utils/media.js";
import { toast } from "../utils/toast.js";

const ROLE_LABELS = {
  student: "Student",
  institution_staff: "Institution staff",
  admin: "Admin",
  super_admin: "Super admin",
};

let currentUser = null;

function fillForm(user) {
  const form = qs("#profile-form");
  form.name.value = user.name || "";
  form.email.value = user.email || "";
  qs("#role").value = ROLE_LABELS[user.role] || user.role || "";
  qs("#institution_affiliation").value = user.institution_affiliation || "";
  qs("#institution").value = user.institution?.name || "Not linked (staff accounts only)";

  const avatarMount = qs("#sidebar-avatar");
  avatarMount.innerHTML = avatarInnerHtml(user.avatar_url) || initials(user);
}

async function handleSave(event) {
  event.preventDefault();
  const form = qs("#profile-form");
  const saveBtn = qs("#save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  try {
    currentUser = await api.patch("/users/me/", {
      name: form.name.value.trim(),
      institution_affiliation: form.institution_affiliation.value.trim() || null,
    });
    clearCurrentUserCache();
    fillForm(currentUser);
    toast.success("Profile updated.");
  } catch (err) {
    if (err instanceof ApiError) {
      applyFieldErrors(form, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not save changes.");
    }
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Changes";
  }
}

async function handleAvatarUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const previewUrl = URL.createObjectURL(file);
  qs("#sidebar-avatar").innerHTML = `<img src="${previewUrl}" alt="">`;

  const formData = new FormData();
  formData.append("avatar", file);

  try {
    currentUser = await api.upload("/users/me/", formData, "PATCH");
    clearCurrentUserCache();
    fillForm(currentUser);
    toast.success("Photo updated.");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not upload photo.");
  } finally {
    event.target.value = "";
  }
}

function showTab(name) {
  qs("#tab-profile").hidden = name !== "profile";
  qs("#tab-preferences").hidden = name !== "preferences";
  document.querySelectorAll(".profile-tabs button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === name);
  });
}

function box(name, value, label, on) {
  return `<label><input type="checkbox" name="${name}" value="${value}" ${on ? "checked" : ""} /> ${escapeHtml(label)}</label>`;
}

async function renderPreferences() {
  const [sections, preference] = await Promise.all([
    api.get("/sections/"),
    api.get("/preferences/me/"),
  ]);
  const browseSections = sections.filter((section) => section.slug !== "college-app-resources");
  const selected = new Set((preference.preferred_categories || []).map((category) => category.id));
  const selectedSections = new Set((preference.sections || []).map((section) => section.id));
  const formats = preference.formats?.length ? preference.formats : ["in_person", "online", "hybrid"];
  const days = preference.days?.length ? preference.days : ["weekdays", "weekends"];
  const onboarding = getQueryParam("onboarding") === "1";
  qs("#onboarding-note").hidden = !onboarding;
  const form = qs("#preferences-form");
  form.innerHTML = `
      <fieldset>
        <legend>Sections</legend>
        ${browseSections
          .map((section) => box("section", section.id, section.name, selectedSections.has(section.id)))
          .join("")}
      </fieldset>
      ${browseSections
        .map(
          (section) => `
        <fieldset>
          <legend>${escapeHtml(section.name)}</legend>
          ${(section.categories || [])
            .map((category) => box("category", category.id, category.name, selected.has(category.id)))
            .join("")}
        </fieldset>`
        )
        .join("")}
      <fieldset>
        <legend>Format</legend>
        ${box("format", "in_person", "In person", formats.includes("in_person"))}
        ${box("format", "online", "Online", formats.includes("online"))}
        ${box("format", "hybrid", "Hybrid", formats.includes("hybrid"))}
      </fieldset>
      <fieldset>
        <legend>Days</legend>
        ${box("days", "weekdays", "Weekdays", days.includes("weekdays"))}
        ${box("days", "weekends", "Weekends", days.includes("weekends"))}
      </fieldset>
      <label>How far will you travel
        <select name="max_distance_km">
          <option value="">Any distance</option>
          ${[10, 25, 50, 100]
            .map(
              (km) =>
                `<option value="${km}" ${Number(preference.max_distance_km) === km ? "selected" : ""}>${km} km</option>`
            )
            .join("")}
        </select>
      </label>
      <label><input type="checkbox" name="include_other_countries" ${preference.include_other_countries ? "checked" : ""} /> Include events outside my country</label>
      <label><input type="checkbox" name="free_only" ${preference.free_only ? "checked" : ""} /> Free only</label>
      <label>Country <input name="country" value="${escapeHtml(preference.country || "Kenya")}" /></label>
      <label>City <input name="city" value="${escapeHtml(preference.city || "")}" /></label>
      <button type="button" class="btn btn-secondary btn-sm" id="use-location">Use my current location</button>
      <label><input type="checkbox" name="email_notifications" ${preference.email_notifications ? "checked" : ""} /> Email notifications</label>
      <button class="btn btn-gold" type="submit" id="finish-preferences">Finish</button>
    `;
  const finish = qs("#finish-preferences");
  const refreshFinish = () => {
    const any = form.querySelectorAll('input[name="category"]:checked').length > 0;
    if (onboarding) finish.disabled = !any;
  };
  form.addEventListener("change", refreshFinish);
  refreshFinish();
  qs("#use-location").addEventListener("click", () => {
    navigator.geolocation?.getCurrentPosition((position) => {
      form.dataset.latitude = position.coords.latitude.toFixed(2);
      form.dataset.longitude = position.coords.longitude.toFixed(2);
      toast.success("Location saved with your preferences.");
    });
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const categoryIds = Array.from(form.querySelectorAll('input[name="category"]:checked')).map((box) => box.value);
    const sectionIds = Array.from(form.querySelectorAll('input[name="section"]:checked')).map((box) => box.value);
    const formatValues = Array.from(form.querySelectorAll('input[name="format"]:checked')).map((box) => box.value);
    const dayValues = Array.from(form.querySelectorAll('input[name="days"]:checked')).map((box) => box.value);
    if (onboarding && categoryIds.length === 0) return;
    if (formatValues.length === 0 || dayValues.length === 0) {
      toast.error("Choose at least one format and one set of days.");
      return;
    }
    const payload = {
      preferred_category_ids: categoryIds,
      section_ids: sectionIds,
      formats: formatValues,
      days: dayValues,
      free_only: form.free_only.checked,
      include_other_countries: form.include_other_countries.checked,
      country: form.country.value,
      city: form.city.value,
      email_notifications: form.email_notifications.checked,
      max_distance_km: form.max_distance_km.value ? Number(form.max_distance_km.value) : null,
    };
    if (form.dataset.latitude && form.dataset.longitude) {
      payload.latitude = form.dataset.latitude;
      payload.longitude = form.dataset.longitude;
    }
    await api.patch("/preferences/me/", payload);
    clearCurrentUserCache();
    toast.success("Preferences saved.");
    if (onboarding) window.location.href = "/index.html";
  });
}

async function init() {
  await renderHeader();
  renderFooter();

  currentUser = await requireAuth();
  if (!currentUser) return;

  fillForm(currentUser);
  document.querySelectorAll('input[type="password"]').forEach((input) => attachPasswordToggle(input));

  qs("#profile-form").addEventListener("submit", handleSave);
  qs("#discard-btn").addEventListener("click", () => fillForm(currentUser));
  qs("#avatar-upload-btn").addEventListener("click", () => qs("#avatar-input").click());
  qs("#avatar-input").addEventListener("change", handleAvatarUpload);
  document.querySelectorAll(".profile-tabs button").forEach((button) => {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  });
  qs("#password-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    await api.post("/users/me/password/", {
      current_password: form.current_password.value,
      new_password: form.new_password.value,
      new_password_confirm: form.new_password_confirm.value,
    });
    toast.success("Password updated.");
    form.reset();
  });
  qs("#delete-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!window.confirm("Delete your account? This cannot be undone.")) return;
    await api.post("/users/me/delete/", { password: event.target.password.value });
    clearCurrentUserCache();
    window.location.href = "/index.html";
  });
  await renderPreferences();
  if (getQueryParam("tab") === "preferences") showTab("preferences");
}

init();
