import { api, ApiError } from "../utils/api.js";
import { applyFieldErrors, formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const form = qs("#register-form");
const submitBtn = qs("#register-submit");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = formToObject(form, { omitEmpty: true });

  submitBtn.disabled = true;
  submitBtn.textContent = "Creating your account...";

  try {
    await api.post("/auth/register/", payload);
    toast.success("Account created. Check your email for a verification code.");
    const email = encodeURIComponent(payload.email || "");
    window.location.href = `/pages/verify-email.html?email=${email}`;
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
