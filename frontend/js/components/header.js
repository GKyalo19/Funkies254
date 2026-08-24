/**
 * Renders the sticky site header (logo, search bar, hamburger/profile menu)
 * into `<div id="site-header"></div>` on every page. One implementation,
 * reused everywhere, so nav changes only need to happen in one file.
 *
 * Matches the Figma nav: circular logo left, pill search centered, a single
 * hamburger trigger on the right that opens a dropdown with either the
 * auth links (logged out) or the account menu (logged in).
 */
import { canManageEvents, displayName, getCurrentUser, initials, logout } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";

function loggedOutMenu() {
  return `
    <a href="/index.html">Home</a>
    <a href="/pages/login.html">Log in</a>
    <a href="/pages/register.html">Register</a>
  `;
}

function loggedInMenu(user) {
  return `
    <a href="/index.html">Home</a>
    <a href="/pages/profile.html">My Profile</a>
    <a href="/pages/preferences.html">Preferences</a>
    <a href="/pages/registrations.html">My Registrations</a>
    ${canManageEvents(user) ? '<a href="/pages/event-form.html">+ Add Event</a>' : ""}
    <button type="button" id="header-logout-btn">Log out</button>
  `;
}

export async function renderHeader(activeSearchValue = "") {
  const mount = document.getElementById("site-header");
  if (!mount) return;

  mount.innerHTML = `
    <header class="site-header">
      <div class="container header-inner">
        <a class="brand" href="/index.html" aria-label="Funkies254 home">
          <img class="brand-logo" src="/assets/images/logo.png" alt="Funkies254 logo" />
        </a>
        <form class="search-bar" id="header-search-form">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/><line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <input type="search" name="q" placeholder="Search events" value="${escapeHtml(activeSearchValue)}" />
        </form>
        <div class="header-actions" id="header-actions">
          <div class="menu-dropdown">
            <button class="icon-btn" id="header-hamburger-btn" type="button" aria-label="Menu">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
            <div class="menu-dropdown-panel" id="header-menu-panel"></div>
          </div>
        </div>
      </div>
    </header>
  `;

  qs("#header-search-form", mount).addEventListener("submit", (event) => {
    event.preventDefault();
    const query = new FormData(event.target).get("q") || "";
    window.location.href = `/pages/event-listings.html?search=${encodeURIComponent(query)}`;
  });

  const panel = qs("#header-menu-panel", mount);
  const hamburgerBtn = qs("#header-hamburger-btn", mount);
  const user = await getCurrentUser();

  if (user) {
    panel.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;padding:10px 14px;">
        <span class="avatar" style="width:36px;height:36px;font-size:14px;">
          ${user.avatar_url ? `<img src="${escapeHtml(user.avatar_url)}" alt="" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">` : initials(user)}
        </span>
        <span style="font-weight:700;">${escapeHtml(displayName(user))}</span>
      </div>
      ${loggedInMenu(user)}
    `;
    qs("#header-logout-btn", mount).addEventListener("click", async () => {
      await logout();
      window.location.href = "/index.html";
    });
  } else {
    panel.innerHTML = loggedOutMenu();
  }

  hamburgerBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    panel.classList.toggle("open");
  });
  document.addEventListener("click", () => panel.classList.remove("open"));
}
