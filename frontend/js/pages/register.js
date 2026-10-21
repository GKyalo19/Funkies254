import { api, ApiError } from "../utils/api.js";
import { applyFieldErrors, attachPasswordToggle, formToObject, qs } from "../utils/dom.js";
import { toast } from "../utils/toast.js";

const form = qs("#register-form");
const submitBtn = qs("#register-submit");

attachPasswordToggle(qs("#password"));
attachPasswordToggle(qs("#password_confirm"));

api.get("/school-levels/").then((levels) => {
  const select = qs("#school_level_id");
  levels
    .filter((level) => level.slug !== "primary")
    .forEach((level) => {
      const option = document.createElement("option");
      option.value = level.id;
      option.textContent = level.name;
      select.appendChild(option);
    });
}).catch(() => {});

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
