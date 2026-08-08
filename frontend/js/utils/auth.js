/**
 * Central place for "who is logged in?" — every page asks this instead of
 * calling /users/me/ directly, so the result can be cached for the page's
 * lifetime (the header, the page script, and any guard all reuse one call).
 */
import { api } from "./api.js";

let cachedUser; // undefined = not checked yet, null = anonymous, object = logged in

export async function getCurrentUser({ force = false } = {}) {
  if (cachedUser !== undefined && !force) return cachedUser;
  try {
    cachedUser = await api.get("/users/me/");
  } catch {
    cachedUser = null;
  }
  return cachedUser;
}

export function clearCurrentUserCache() {
  cachedUser = undefined;
}

/** Call at the top of any page that requires login (profile, preferences). */
export async function requireAuth(redirectTo = "/pages/login.html") {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = redirectTo;
    return null;
  }
  return user;
}

export async function logout() {
  try {
    await api.post("/auth/logout/");
  } finally {
    clearCurrentUserCache();
  }
}

export function initials(user) {
  if (!user) return "?";
  const name = (user.full_name || user.email || "").trim();
  const parts = name.split(" ").filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}
