import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { requireAuth } from "../utils/auth.js";
import { applyFieldErrors, formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

let selectedCategoryIds = [];
let createdEventSlug = null;

async function loadFormOptions() {
  const [organizers, categories] = await Promise.all([
    api.get("/organizers/?page_size=100"),
    api.get("/events/categories/"),
  ]);

  const organizerSelect = qs("#organizer");
  organizerSelect.innerHTML = organizers.results
    .map((org) => `<option value="${org.id}">${org.name}</option>`)
    .join("");

  const categoriesField = qs("#categories-field");
  categoriesField.innerHTML = categories
    .map((cat) => `<span class="tag" data-id="${cat.id}">${cat.name}</span>`)
    .join("");
  categoriesField.querySelectorAll(".tag").forEach((tagEl) => {
    tagEl.addEventListener("click", () => {
      const id = Number(tagEl.dataset.id);
      selectedCategoryIds = selectedCategoryIds.includes(id)
        ? selectedCategoryIds.filter((v) => v !== id)
        : [...selectedCategoryIds, id];
      tagEl.classList.toggle("selected");
    });
  });
}

function buildPayload(form) {
  const raw = formToObject(form);
  return {
    ...raw,
    organizer: Number(raw.organizer),
    categories: selectedCategoryIds,
    registration_fee: raw.registration_fee || "0",
    capacity: raw.capacity ? Number(raw.capacity) : null,
    end_datetime: raw.end_datetime || null,
    is_featured: form.is_featured.checked,
    start_datetime: new Date(raw.start_datetime).toISOString(),
    ...(raw.end_datetime ? { end_datetime: new Date(raw.end_datetime).toISOString() } : {}),
  };
}

async function handleSubmit(event) {
  event.preventDefault();
  const form = qs("#event-form");
  const submitBtn = qs("#submit-btn");
  submitBtn.disabled = true;
  submitBtn.textContent = "Creating...";

  try {
    const created = await api.post("/events/", buildPayload(form));
    createdEventSlug = created.slug;
    toast.success("Event created! Add a cover image below, or you're done.");
    qs("#cover-upload-section").style.display = "block";
    form.querySelectorAll("input, select, textarea, button").forEach((el) => (el.disabled = true));
  } catch (err) {
    if (err instanceof ApiError) {
      applyFieldErrors(form, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not reach the server.");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Create Event";
  }
}

async function handleCoverUpload(event) {
  const file = event.target.files[0];
  if (!file || !createdEventSlug) return;

  const formData = new FormData();
  formData.append("cover_image", file);

  try {
    await api.upload(`/events/${createdEventSlug}/cover-image/`, formData);
    toast.success("Cover image uploaded.");
    window.location.href = `/pages/event.html?slug=${createdEventSlug}`;
  } catch (err) {
    toast.error(err.message);
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  const user = await requireAuth();
  if (!user) return;

  if (!user.is_staff) {
    document.querySelector("main").innerHTML = `<div class="empty-state">Only staff accounts can add events. Contact an admin if you think this is a mistake.</div>`;
    return;
  }

  await loadFormOptions();
  qs("#event-form").addEventListener("submit", handleSubmit);
  qs("#cover-image-input").addEventListener("change", handleCoverUpload);
}

init();
