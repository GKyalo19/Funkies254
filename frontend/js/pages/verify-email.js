import { api, ApiError } from "../utils/api.js";
import { clearCurrentUserCache } from "../utils/auth.js";
import { applyFieldErrors, getQueryParam, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const form = qs("#verify-form");
const submitBtn = qs("#verify-submit");
const resendBtn = qs("#resend-btn");
const emailInput = qs("#email");
const codeInput = qs("#code");
const copy = qs("#verify-copy");

const emailFromQuery = (getQueryParam("email") || "").trim();
if (emailFromQuery) {
  emailInput.value = emailFromQuery;
  copy.textContent = `Enter the 6-digit code we sent to ${emailFromQuery}.`;
  codeInput.focus();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  submitBtn.disabled = true;
  submitBtn.textContent = "Verifying...";

  try {
    await api.post("/auth/verify-email/", {
      email: emailInput.value.trim(),
      code: codeInput.value.trim(),
    });
    clearCurrentUserCache();
    toast.success("Email verified. Welcome!");
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
    submitBtn.textContent = "Verify";
  }
});

resendBtn.addEventListener("click", async () => {
  const email = emailInput.value.trim();
  if (!email) {
    toast.error("Enter your email first.");
    emailInput.focus();
    return;
  }

  resendBtn.disabled = true;
  try {
    await api.post("/auth/resend-verification/", { email });
    toast.success("If that inbox is waiting to be verified, a new code is on its way.");
    startResendCooldown(60);
  } catch (err) {
    resendBtn.disabled = false;
    toast.error(err instanceof ApiError ? err.message : "Could not resend the code.");
  }
});

function startResendCooldown(seconds) {
  let remaining = seconds;
  resendBtn.disabled = true;
  const tick = () => {
    if (remaining <= 0) {
      resendBtn.disabled = false;
      resendBtn.textContent = "Resend code";
      return;
    }
    resendBtn.textContent = `Resend code (${remaining}s)`;
    remaining -= 1;
    window.setTimeout(tick, 1000);
  };
  tick();
}
