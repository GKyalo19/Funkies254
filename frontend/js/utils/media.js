/** Helpers for event covers and avatars stored in Supabase. */
import { escapeHtml } from "./dom.js";

/**
 * Cover <img>, or a CSS placeholder when the event has no uploaded image.
 * Broken remote URLs drop the <img> so the parent `.cover` gradient shows.
 */
export function coverInnerHtml(url, alt = "") {
  if (!url) return `<div class="cover-fallback" aria-hidden="true"></div>`;
  return (
    `<img src="${escapeHtml(url)}" alt="${escapeHtml(alt)}" loading="lazy" ` +
    `referrerpolicy="no-referrer" onerror="this.onerror=null;this.remove();" />`
  );
}

/** Avatar <img>, or empty so the parent `.avatar` initials/background remain. */
export function avatarInnerHtml(url) {
  if (!url) return "";
  return (
    `<img src="${escapeHtml(url)}" alt="" referrerpolicy="no-referrer" ` +
    `onerror="this.onerror=null;this.remove();" />`
  );
}
