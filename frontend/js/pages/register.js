import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache } from "../utils/auth.js";
import { applyFieldErrors, escapeHtml, formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const form = qs("#register-form");
const submitBtn = qs("#register-submit");

/** The API links accounts to institutions by id, so the picker needs the real list. */
async function loadInstitutions() {
  try {
    const data = await api.get("/institutions/?page_size=100");
    qs("#institution_id").innerHTML =
      `<option value="">Organization / Institution (optional)</option>` +
      data.results
        .map((inst) => `<option value="${escapeHtml(inst.id)}">${escapeHtml(inst.name)}</option>`)
        .join("");
  } catch {
    // Institution is optional — leave the single placeholder option in place.
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formToObject(form, { omitEmpty: true });

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating your account...";

  try {
    await api.post("/auth/register/", payload);
    clearCurrentUserCache();
    toast.success("Account created! Let's set your preferences.");
    window.location.href = "/pages/preferences.html";
  } catch (err) {
    if (err instanceof ApiError) {
      applyFieldErrors(form, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not reach the server. Please try again.");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Register";
  }
});

loadInstitutions();
