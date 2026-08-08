import { api, ApiError } from "../utils/api.js";
import { applyFieldErrors, formToObject, getQueryParam, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const uid = getQueryParam("uid");
const token = getQueryParam("token");

if (uid && token) {
  qs("#request-step").style.display = "none";
  qs("#confirm-step").style.display = "block";
} else {
  qs("#confirm-step").style.display = "none";
}

const requestForm = qs("#request-form");
requestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitBtn = qs("#request-submit");
  submitBtn.disabled = true;
  submitBtn.textContent = "Sending...";

  try {
    await api.post("/auth/password-reset/request/", formToObject(requestForm));
    requestForm.style.display = "none";
    qs("#request-confirmation").style.display = "block";
  } catch (err) {
    toast.error(err instanceof ApiError ? err.message : "Could not reach the server.");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Send reset link";
  }
});

const confirmForm = qs("#confirm-form");
confirmForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitBtn = qs("#confirm-submit");
  submitBtn.disabled = true;
  submitBtn.textContent = "Resetting...";

  try {
    await api.post("/auth/password-reset/confirm/", { uid, token, ...formToObject(confirmForm) });
    toast.success("Password reset! You can now log in.");
    window.location.href = "/pages/login.html";
  } catch (err) {
    if (err instanceof ApiError) {
      applyFieldErrors(confirmForm, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not reach the server.");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Reset password";
  }
});
