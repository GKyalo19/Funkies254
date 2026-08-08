/** Small DOM helpers used across every page — avoids repeating boilerplate. */

export const qs = (selector, scope = document) => scope.querySelector(selector);
export const qsa = (selector, scope = document) => Array.from(scope.querySelectorAll(selector));

/** Escapes text before it's interpolated into innerHTML, to avoid XSS from event titles/descriptions. */
export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

/** Reads a query param from the current URL, e.g. getQueryParam("slug"). */
export function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name);
}

/** Serialises a <form> into a plain object, skipping empty optional fields. */
export function formToObject(form) {
  const data = {};
  new FormData(form).forEach((value, key) => {
    data[key] = value;
  });
  return data;
}

/** Applies a field-level validation error message returned by the API (ApiError.fields). */
export function applyFieldErrors(form, fields) {
  qsa(".field", form).forEach((field) => field.classList.remove("has-error"));
  if (!fields) return;
  Object.entries(fields).forEach(([name, messages]) => {
    const input = form.querySelector(`[name="${name}"]`);
    if (!input) return;
    const field = input.closest(".field");
    if (!field) return;
    field.classList.add("has-error");
    const errorEl = qs(".error-text", field);
    if (errorEl) errorEl.textContent = Array.isArray(messages) ? messages[0] : messages;
  });
}

export function formatDate(isoString) {
  const date = new Date(isoString);
  return date.toLocaleDateString("en-KE", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

/** Compact date for event cards, e.g. "Nov 27th". */
export function formatShortDate(isoString) {
  const date = new Date(isoString);
  const day = date.getDate();
  const suffix = day % 10 === 1 && day !== 11 ? "st" : day % 10 === 2 && day !== 12 ? "nd" : day % 10 === 3 && day !== 13 ? "rd" : "th";
  return `${date.toLocaleDateString("en-KE", { month: "short" })} ${day}${suffix}`;
}

export function formatTimeRange(startIso, endIso) {
  const start = new Date(startIso);
  const startTime = start.toLocaleTimeString("en-KE", { hour: "numeric", minute: "2-digit" });
  if (!endIso) return startTime;
  const end = new Date(endIso);
  const endTime = end.toLocaleTimeString("en-KE", { hour: "numeric", minute: "2-digit" });
  return `${startTime} - ${endTime}`;
}

export function formatFee(fee) {
  const amount = Number(fee);
  if (amount === 0) return "Free";
  return `KES ${amount.toLocaleString()}`;
}
