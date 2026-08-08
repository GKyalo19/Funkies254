import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache, initials, requireAuth } from "../utils/auth.js";
import { formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

let currentUser = null;

function fillForm(user) {
  const form = qs("#profile-form");
  form.first_name.value = user.first_name || "";
  form.last_name.value = user.last_name || "";
  form.email.value = user.email || "";
  form.institution.value = user.institution || "";
  form.education_level.value = user.education_level || "high_school";
  form.phone_number.value = user.phone_number || "";

  const avatarMount = qs("#sidebar-avatar");
  avatarMount.innerHTML = user.avatar_url
    ? `<img src="${user.avatar_url}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`
    : initials(user);
}

async function handleSave(event) {
  event.preventDefault();
  const form = qs("#profile-form");
  const saveBtn = qs("#save-btn");
  saveBtn.disabled = true;
  saveBtn.textContent = "Saving...";

  const payload = formToObject(form);
  delete payload.email; // read-only field, never sent

  try {
    currentUser = await api.patch("/users/me/", payload);
    clearCurrentUserCache();
    toast.success("Profile updated.");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not save changes.");
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Changes";
  }
}

async function handleAvatarUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("avatar", file);

  try {
    currentUser = await api.upload("/users/me/avatar/", formData);
    clearCurrentUserCache();
    fillForm(currentUser);
    toast.success("Photo updated.");
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not upload photo.");
  }
}

async function init() {
  await renderHeader();
  renderFooter();

  currentUser = await requireAuth();
  if (!currentUser) return;

  fillForm(currentUser);

  qs("#profile-form").addEventListener("submit", handleSave);
  qs("#discard-btn").addEventListener("click", () => fillForm(currentUser));
  qs("#avatar-upload-btn").addEventListener("click", () => qs("#avatar-input").click());
  qs("#avatar-input").addEventListener("change", handleAvatarUpload);
}

init();
