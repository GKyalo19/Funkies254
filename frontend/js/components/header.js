/**
 * Sticky header: hamburger, logo, search, then the account area on the right.
 */
import { canManageEvents, firstName, getCurrentUser, initials, isAdmin, isInstitutionStaff, logout } from "../utils/auth.js";
import { escapeHtml, qs } from "../utils/dom.js";
import { avatarInnerHtml } from "../utils/media.js";

const SECTIONS = [
  ["College Events", "college-events"],
  ["High School Events", "high-school-events"],
  ["College Application Resources", "college-app-resources"],
];

function sectionLinks() {
  return SECTIONS.map(
    ([label, slug]) =>
      `<a href="/pages/event-listings.html?section=${slug}">${escapeHtml(label)}</a>`
  ).join("");
}

function visitorMenu() {
  return `
    <a href="/index.html">Home</a>
    ${sectionLinks()}
    <a href="/pages/login.html">Log in</a>
    <a href="/pages/register.html">Register</a>
  `;
}

function studentMenu() {
  return `
    <a href="/index.html">Home</a>
    ${sectionLinks()}
    <a href="/pages/saved-events.html">Saved Events</a>
    <a href="/pages/profile.html">My Profile</a>
    <button type="button" id="header-logout-btn">Log Out</button>
  `;
}

function staffMenu(user) {
  const add = canManageEvents(user) ? '<a href="/pages/event-form.html">+ Add Event</a>' : "";
  return `
    ${studentMenu().replace('<button type="button" id="header-logout-btn">Log Out</button>', "")}
    <a href="/pages/events-dashboard.html">My Events</a>
    ${add}
    <button type="button" id="header-logout-btn">Log Out</button>
  `;
}

function adminMenu(user) {
  return `
    <a href="/index.html">Home</a>
    ${sectionLinks()}
    <a href="/pages/saved-events.html">Saved Events</a>
    <a href="/pages/profile.html">My Profile</a>
    <a href="/pages/event-form.html">+ Add Event</a>
    <p class="menu-label">Admin</p>
    <a href="/pages/review-queue.html">Review Queue</a>
    <a href="/pages/site-health.html">Site Health</a>
    <a href="/pages/events-dashboard.html">All Events dashboard</a>
    <a href="/pages/users.html">Users</a>
    <a href="https://funkies254-api.onrender.com/admin/events/category/" target="_blank" rel="noopener">Categories</a>
    <button type="button" id="header-logout-btn">Log Out</button>
  `;
}

function menuFor(user) {
  if (!user) return visitorMenu();
  if (isAdmin(user)) return adminMenu(user);
  if (isInstitutionStaff(user)) return staffMenu(user);
  return studentMenu();
}

function accountArea(user) {
  if (!user) {
    return `<a class="btn btn-primary btn-sm header-login" href="/pages/login.html">Log in / Register</a>`;
  }
  const avatar = avatarInnerHtml(user.avatar_url) || escapeHtml(initials(user));
  return `
    <a class="header-account" href="/pages/profile.html">
      <span class="header-account-name">${escapeHtml(firstName(user))}</span>
      <span class="avatar header-avatar">${avatar}</span>
    </a>
  `;
}

export async function renderHeader(activeSearchValue = "") {
  const mount = document.getElementById("site-header");
  if (!mount) return;

  mount.innerHTML = `
    <header class="site-header" id="site-header-bar">
      <div class="container header-inner">
        <button class="icon-btn" id="header-hamburger-btn" type="button" aria-label="Menu" aria-expanded="false">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none"><line x1="3" y1="6" x2="21" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="3" y1="18" x2="21" y2="18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
        </button>
        <a class="brand" href="/index.html" aria-label="Funkies 254 home">
          <img class="brand-logo" src="/assets/images/logo.png" alt="" />
          <span class="brand-wordmark">Funkies 254</span>
        </a>
        <form class="search-bar" id="header-search-form">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="11" cy="11" r="7" stroke="currentColor" stroke-width="2"/><line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
          <input type="search" name="q" placeholder="Search events" value="${escapeHtml(activeSearchValue)}" />
        </form>
        <div class="header-actions" id="header-actions"></div>
        <div class="menu-dropdown-panel" id="header-menu-panel"></div>
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
  const path = window.location.pathname;
  if (
    user?.role === "student" &&
    user.has_preferences === false &&
    !path.endsWith("/profile.html") &&
    !path.endsWith("/verify-email.html") &&
    !path.endsWith("/login.html") &&
    !path.endsWith("/register.html")
  ) {
    window.location.href = "/pages/profile.html?tab=preferences&onboarding=1";
    return;
  }
  qs("#header-actions", mount).innerHTML = accountArea(user);
  panel.innerHTML = menuFor(user);

  const logoutBtn = qs("#header-logout-btn", mount);
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await logout();
      window.location.href = "/index.html";
    });
  }

  hamburgerBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    const open = panel.classList.toggle("open");
    hamburgerBtn.setAttribute("aria-expanded", open ? "true" : "false");
  });
  document.addEventListener("click", () => {
    panel.classList.remove("open");
    hamburgerBtn.setAttribute("aria-expanded", "false");
  });

  const bar = qs("#site-header-bar", mount);
  const onScroll = () => bar.classList.toggle("is-scrolled", window.scrollY > 80);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });
}
