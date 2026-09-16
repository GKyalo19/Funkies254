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

/**
 * Serialises a <form> into a plain object.
 *
 * With `{ omitEmpty: true }`, blank inputs are left out entirely — needed for
 * optional nullable API fields that reject "" but accept an absent key.
 */
export function formToObject(form, { omitEmpty = false } = {}) {
  const data = {};
  new FormData(form).forEach((value, key) => {
    if (omitEmpty && typeof value === "string" && value.trim() === "") return;
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

/** Returns a valid Date, or null — so a missing/garbled timestamp renders as "" rather than "Invalid Date". */
function parseDate(isoString) {
  if (!isoString) return null;
  const date = new Date(isoString);
  return Number.isNaN(date.getTime()) ? null : date;
}

const DISPLAY_TZ = "Africa/Nairobi";

export function formatDate(isoString) {
  const date = parseDate(isoString);
  if (!date) return "";
  return date.toLocaleDateString("en-KE", {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: DISPLAY_TZ,
  });
}

/** "Fri, 20 Sep 2026 - Sat, 21 Sep 2026". Always includes the end date when one is set. */
export function formatDateRange(startIso, endIso) {
  const start = formatDate(startIso);
  if (!start) return "";
  const end = formatDate(endIso);
  if (!end) return start;
  return `${start} - ${end}`;
}

/** Compact date for event cards, e.g. "Nov 27th". */
export function formatShortDate(isoString) {
  const date = parseDate(isoString);
  if (!date) return "";
  const day = Number(
    new Intl.DateTimeFormat("en-KE", { day: "numeric", timeZone: DISPLAY_TZ }).format(date)
  );
  const suffix = day % 10 === 1 && day !== 11 ? "st" : day % 10 === 2 && day !== 12 ? "nd" : day % 10 === 3 && day !== 13 ? "rd" : "th";
  const month = date.toLocaleDateString("en-KE", { month: "short", timeZone: DISPLAY_TZ });
  return `${month} ${day}${suffix}`;
}

/** Compact range for event cards, e.g. "Nov 27th - Nov 29th". */
export function formatShortDateRange(startIso, endIso) {
  const start = formatShortDate(startIso);
  if (!start) return "";
  const end = formatShortDate(endIso);
  if (!end || end === start) return start;
  return `${start} - ${end}`;
}

export function formatTimeRange(startIso, endIso) {
  const start = parseDate(startIso);
  if (!start) return "";
  const opts = { hour: "numeric", minute: "2-digit", timeZone: DISPLAY_TZ };
  const startTime = start.toLocaleTimeString("en-KE", opts);
  const end = parseDate(endIso);
  if (!end) return startTime;
  const endTime = end.toLocaleTimeString("en-KE", opts);
  return `${startTime} - ${endTime}`;
}

/** Formats an ISO timestamp for a <input type="datetime-local"> value, in local time. */
export function toDatetimeLocalValue(isoString) {
  const date = parseDate(isoString);
  if (!date) return "";
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
