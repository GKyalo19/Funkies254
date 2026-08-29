import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { canManageEvents, isInstitutionStaff, requireAuth } from "../utils/auth.js";
import { applyFieldErrors, escapeHtml, getQueryParam, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

let selectedCategoryIds = [];
let editingSlug = null;

function toDatetimeLocal(isoString) {
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function loadFormOptions(user, existingEvent) {
  const [institutions, categories, schoolLevels] = await Promise.all([
    api.get("/institutions/?page_size=100"),
    api.get("/categories/"),
    api.get("/school-levels/"),
  ]);

  const institutionSelect = qs("#institution_id");
  const options =
    isInstitutionStaff(user) && user.institution ? [user.institution] : institutions.results;
  institutionSelect.innerHTML = options
    .map((inst) => `<option value="${escapeHtml(inst.id)}">${escapeHtml(inst.name)}</option>`)
    .join("");
  if (options.length === 1) institutionSelect.disabled = true;

  qs("#school_level_id").innerHTML =
    `<option value="">Any level</option>` +
    schoolLevels
      .map((level) => `<option value="${escapeHtml(level.id)}">${escapeHtml(level.name)}</option>`)
      .join("");

  const categoriesField = qs("#categories-field");
  categoriesField.innerHTML = categories
    .map((cat) => `<span class="tag" data-id="${escapeHtml(cat.id)}">${escapeHtml(cat.name)}</span>`)
    .join("");
  categoriesField.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => {
      const id = tagEl.dataset.id;
      selectedCategoryIds = selectedCategoryIds.includes(id)
        ? selectedCategoryIds.filter((v) => v !== id)
        : [...selectedCategoryIds, id];
      tagEl.classList.toggle("selected");
    });
  });

  if (existingEvent) fillForm(existingEvent);
}

function fillForm(event) {
  const form = qs("#event-form");
  form.title.value = event.title || "";
  form.description.value = event.description || "";
  if (event.institution?.id) form.institution_id.value = event.institution.id;
  form.school_level_id.value = event.school_level?.id || "";
  form.venue.value = event.venue || "";
  form.location.value = event.location || "";
  form.registration_link.value = event.registration_link || "";
  form.start_time.value = toDatetimeLocal(event.start_time);
  form.end_time.value = toDatetimeLocal(event.end_time);
  qs("#is_virtual").checked = Boolean(event.is_virtual);

  selectedCategoryIds = (event.categories || []).map((cat) => cat.id);
  qs("#categories-field")
    .querySelectorAll(".tag")
    .forEach((tagEl) => {
      tagEl.classList.toggle("selected", selectedCategoryIds.includes(tagEl.dataset.id));
    });

  if (event.cover_image_url) {
    qs("#cover-preview").hidden = false;
    qs("#cover-preview-img").src = event.cover_image_url;
  }
}

/** Virtual events must not carry physical location data (§10.1). */
function wireVirtualToggle() {
  const checkbox = qs("#is_virtual");
  const physicalFields = qs("#physical-fields");
  const linkHint = qs("#link-required-hint");

  const sync = () => {
    const isVirtual = checkbox.checked;
    physicalFields.style.display = isVirtual ? "none" : "block";
    linkHint.style.display = isVirtual ? "inline" : "none";
    if (isVirtual) {
      qs("#venue").value = "";
      qs("#location").value = "";
    }
  };

  checkbox.addEventListener("change", sync);
  sync();
}

function wireCoverPreview() {
  const input = qs("#cover_image");
  const preview = qs("#cover-preview");
  const img = qs("#cover-preview-img");
  input.addEventListener("change", () => {
    const file = input.files[0];
    if (!file) return;
    img.src = URL.createObjectURL(file);
    preview.hidden = false;
  });
}

function buildFormData(form) {
  const isVirtual = qs("#is_virtual").checked;
  const data = new FormData();

  data.append("title", form.title.value.trim());
  data.append("description", form.description.value.trim());
  data.append("institution_id", form.institution_id.value);
  data.append("is_virtual", isVirtual ? "true" : "false");
  data.append("start_time", new Date(form.start_time.value).toISOString());
  data.append("end_time", new Date(form.end_time.value).toISOString());

  if (form.school_level_id.value) data.append("school_level_id", form.school_level_id.value);
  if (form.registration_link.value.trim()) {
    data.append("registration_link", form.registration_link.value.trim());
  }

  if (!isVirtual) {
    if (form.venue.value.trim()) data.append("venue", form.venue.value.trim());
    if (form.location.value.trim()) data.append("location", form.location.value.trim());
  }

  selectedCategoryIds.forEach((id) => data.append("category_ids", id));

  const coverFile = form.cover_image.files[0];
  if (coverFile) data.append("cover_image", coverFile);

  return data;
}

async function handleSubmit(event) {
  event.preventDefault();
  const form = qs("#event-form");
  const submitBtn = qs("#submit-btn");

  if (!form.start_time.value || !form.end_time.value) {
    toast.error("Please provide both a start and an end time.");
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = editingSlug ? "Saving..." : "Creating...";

  try {
    const payload = buildFormData(form);
    const saved = editingSlug
      ? await api.upload(`/events/${editingSlug}/`, payload, "PATCH")
      : await api.upload("/events/", payload);
    toast.success(editingSlug ? "Event updated." : "Event created — awaiting admin verification.");
    window.location.href = `/pages/event.html?slug=${encodeURIComponent(saved.slug)}`;
  } catch (err) {
    if (err instanceof ApiError) {
      applyFieldErrors(form, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not reach the server.");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = editingSlug ? "Save changes" : "Create Event";
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  if (!canManageEvents(user)) {
    document.querySelector("main").innerHTML = `<div class="empty-state">Only institution staff and administrators can add events. Contact an admin if you think this is a mistake.</div>`;
    return;
  }

  if (isInstitutionStaff(user) && !user.institution) {
    document.querySelector("main").innerHTML = `<div class="empty-state">Your account is not linked to an institution yet. Ask a super administrator to promote/link you before creating events.</div>`;
    return;
  }

  editingSlug = getQueryParam("slug");
  let existingEvent = null;
  if (editingSlug) {
    try {
      existingEvent = await api.get(`/events/${editingSlug}/`);
    } catch {
      toast.error("Could not load that event.");
      return;
    }
    qs("#event-form-heading").textContent = "Edit Event";
    qs("#event-form-intro").textContent = "Update the listing. Students only see verified events.";
    qs("#submit-btn").textContent = "Save changes";
    document.title = "Edit Event — Funkies254";
  }

  try {
    await loadFormOptions(user, existingEvent);
  } catch {
    toast.error("Could not load the form options.");
    return;
  }

  qs("#event-form-page").hidden = false;
  wireVirtualToggle();
  wireCoverPreview();
  qs("#event-form").addEventListener("submit", handleSubmit);
}

init();
