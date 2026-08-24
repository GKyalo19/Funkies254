/**
 * Thin fetch() wrapper that every page uses to talk to the Django API.
 *
 * Three responsibilities that would otherwise be duplicated on every page:
 *  1. Always send/receive the httpOnly auth cookies (`credentials: "include"`).
 *  2. On a 401, transparently try `/auth/token/refresh/` once, then retry the
 *     original request — so a short-lived access token never logs the user
 *     out mid-session as long as their refresh token is still valid.
 *  3. Normalise errors into one `ApiError` shape so every page can just do
 *     `catch (err) { showToast(err.message) }` without special-casing.
 */
import { API_BASE_URL } from "./config.js";

export class ApiError extends Error {
  constructor(message, status, fields, code) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields || null;
    this.code = code || null;
  }
}

const UNSAFE_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);

function readCookie(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.slice(name.length + 1);
}

async function parseBody(response) {
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

async function refreshAccessToken() {
  const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
    method: "POST",
    credentials: "include",
  });
  return response.ok;
}

async function request(path, { method = "GET", body, isFormData = false, allowRetry = true } = {}) {
  const options = { method, credentials: "include", headers: {} };

  if (body !== undefined) {
    if (isFormData) {
      options.body = body; // Browser sets the multipart Content-Type + boundary automatically.
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
  }

  // Production runs with JWT_COOKIE_CSRF_ENFORCED=True, so cookie-authenticated
  // writes must echo the csrftoken cookie back as a header.
  if (UNSAFE_METHODS.has(method)) {
    const csrfToken = readCookie("csrftoken");
    if (csrfToken) options.headers["X-CSRFToken"] = csrfToken;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, options);

  if (response.status === 401 && allowRetry && !path.startsWith("/auth/")) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request(path, { method, body, isFormData, allowRetry: false });
    }
  }

  const data = await parseBody(response);

  if (!response.ok) {
    // The API's error envelope is {detail, code, errors?} — see
    // backend/apps/common/exceptions.py.
    const message = data?.detail || "Something went wrong. Please try again.";
    throw new ApiError(message, response.status, data?.errors || null, data?.code || null);
  }

  return data;
}

export const api = {
  get: (path) => request(path),
  post: (path, body, opts = {}) => request(path, { method: "POST", body, ...opts }),
  patch: (path, body, opts = {}) => request(path, { method: "PATCH", body, ...opts }),
  put: (path, body, opts = {}) => request(path, { method: "PUT", body, ...opts }),
  delete: (path) => request(path, { method: "DELETE" }),
  /** For multipart/form-data uploads (avatar, event cover images). */
  upload: (path, formData, method = "POST") =>
    request(path, { method, body: formData, isFormData: true }),
};
