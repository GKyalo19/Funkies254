import { renderFooter } from "../components/footer.js";
import { renderHeader } from "../components/header.js";
import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache, initials, requireAuth } from "../utils/auth.js";
import { applyFieldErrors, qs } from "../utils/dom.js";
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
  qs("#institution").value = user.institution?.name || "Not linked to an institution";

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
    // `name` is the only self-editable field on /users/me/.
    currentUser = await api.patch("/users/me/", { name: form.name.value.trim() });
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
