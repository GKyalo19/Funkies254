import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache } from "../utils/auth.js";
import { applyFieldErrors, attachPasswordToggle, formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const form = qs("#login-form");
const submitBtn = qs("#login-submit");
attachPasswordToggle(qs("#password"));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formToObject(form);

  submitBtn.disabled = true;
  submitBtn.textContent = "Logging in...";

  try {
    await api.post("/auth/login/", payload);
    clearCurrentUserCache();
    const params = new URLSearchParams(window.location.search);
    const saveId = params.get("save");
    if (saveId) {
      try {
        await api.post(`/events/${saveId}/save/`, {});
      } catch {
        // The event page can still be opened if the save did not stick.
      }
    }
    toast.success("Welcome back!");
    const next = params.get("next");
    window.location.href = next && next.startsWith("/") ? next : "/index.html";
  } catch (err) {
    if (err instanceof ApiError) {
      if (err.code === "email_not_verified") {
        const email = encodeURIComponent(payload.email || "");
        toast.error("Please verify your email first. We can resend the code on the next page.");
        window.location.href = `/pages/verify-email.html?email=${email}`;
        return;
      }
      applyFieldErrors(form, err.fields);
      toast.error(err.message);
    } else {
      toast.error("Could not reach the server. Please try again.");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Log In";
  }
});
