# Funkies254 — File Guide

A file-by-file map of the repository: what lives where, and what each file is
responsible for. Use this when you need to find "the file that does X" without
re-reading the whole codebase.

For the *why* behind these choices (tech stack, request flow, data model),
see [`ARCHITECTURE.md`](ARCHITECTURE.md). This doc is the *where*.

> **Rule of thumb while editing:** frontend pages come in a pair — a `.html`
> file in `frontend/pages/` (the markup/skeleton) and a matching `.js` file in
> `frontend/js/pages/` (the behaviour). Backend features come in a group of
> five — `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py` — all
> inside one `backend/apps/<name>/` folder. Once you know that pattern, the
> rest of this guide is mostly for looking up exact filenames.

---

## 1. Repository root

```
Funkies254 Dev/
├── README.md              Project overview + quick start (read this first)
├── .gitignore              Files/folders git ignores (venv, .env, db.sqlite3, node_modules...)
├── backend/                Django + DRF REST API (see §2 below)
├── frontend/               Vanilla HTML/CSS/JS client (see §3 below)
└── docs/                   All documentation, including this file (see §4 below)
```

---

## 2. `backend/` — Django REST API

```
backend/
├── manage.py                  Django's CLI entrypoint — run everything through this
│                               (migrate, runserver, createsuperuser, seed_demo_data)
├── requirements.txt            Production Python dependencies (installed on Render)
├── requirements-dev.txt        + pytest, pytest-django, faker — local/dev only
├── pytest.ini                  pytest config (points at config.settings, reuses DB)
├── conftest.py                 Shared pytest fixtures (roles, institution, event, login)
├── .env.example                 Template for your own backend/.env (copy, don't edit this one)
├── .env                          Your real local secrets — gitignored, never commit
├── db.sqlite3                    Local SQLite fallback used when DATABASE_URL is blank
├── Procfile                       Tells Render how to run gunicorn + release migrations
├── render.yaml                    Render "infra as code" — declares the web service + env vars
│
├── config/                        The Django "project" — global settings, not a feature
│   ├── settings.py                 THE config file: installed apps, Supabase DB connection,
│   │                                DRF defaults, JWT lifetimes and cookie flags, CORS/CSRF,
│   │                                Supabase Storage credentials, upload limits
│   ├── urls.py                      Root URL router — /admin/, /api/health/, /api/auth/ and
│   │                                the per-app includes mounted under /api/
│   ├── wsgi.py                      Entrypoint gunicorn uses in production (via Procfile)
│   └── asgi.py                      Async entrypoint (present for completeness; unused for now)
│
└── apps/                          One Django app per area of the domain
    ├── common/                     Shared foundation used by every other app
    │   ├── enums.py                 THE controlled vocabularies: UserRole, RegistrationStatus,
    │   │                             AuditAction, SchoolLevelSlug — defined once, imported
    │   │                             everywhere, so filters/analytics never drift
    │   ├── models.py                 UUIDPrimaryKeyModel + TimeStampedModel abstract bases,
    │   │                             and AdminActivityLog (the audit table)
    │   ├── audit.py                  log_action() — the single way an audit row gets written
    │   ├── permissions.py            IsStudent / IsInstitutionStaff / IsAdmin / IsSuperAdmin /
    │   │                             IsStaffOrReadOnly / IsEventOwner / IsInstitutionOwner
    │   ├── exceptions.py             Domain exceptions + the one JSON error envelope:
    │   │                             { "detail": "...", "code": "...", "errors": {...} }
    │   ├── pagination.py             DefaultPagination (page/page_size, max 100)
    │   ├── db.py                     for_update() — row locking on PostgreSQL, no-op on SQLite
    │   ├── supabase_storage.py       Upload/replace/delete against Supabase Storage's REST API,
    │   │                             plus file type/size validation and server-side object paths
    │   ├── serializers.py, views.py, urls.py   Read-only audit log endpoint for the admin dashboard
    │   ├── admin.py                  AdminActivityLog admin (read-only)
    │   └── management/commands/seed_demo_data.py   Idempotent reference + demo data
    │
    ├── users/                       Accounts and authentication
    │   ├── models.py                  Custom User (UUID pk, email login, role, institution FK)
    │   ├── managers.py                 UserManager — create_user/create_superuser, email normalising
    │   ├── authentication.py           CookieJWTAuthentication — reads the access token from the
    │   │                                httpOnly cookie and enforces CSRF on cookie-authed writes
    │   ├── tokens.py                    Token issuing + cookie set/clear/blacklist helpers
    │   ├── services.py                   register_user, set_user_active, change_user_role
    │   ├── serializers.py                 Register/Login/User/UserAdmin/RoleChange serializers
    │   ├── views.py                        Register, Login, TokenRefresh, Logout, Csrf, Me,
    │   │                                    UserList, Suspend, Reinstate, Role
    │   ├── auth_urls.py                    Routes under /api/auth/
    │   ├── urls.py                          Routes under /api/users/
    │   ├── admin.py                          UserAdmin (email, name, role, institution, active)
    │   └── migrations/                        Schema history for this app
    │
    ├── organizers/                    Institutions — the hosts of events
    │   ├── models.py                    Institution (name, unique slug, contact, logo, verified)
    │   ├── services.py                   create/update/verify + the audit records they write
    │   ├── serializers.py                 InstitutionSerializer + a brief nested form
    │   ├── views.py                        Public list/detail, admin create, owner PATCH, verify
    │   ├── urls.py                          Routes under /api/institutions/
    │   ├── admin.py                          InstitutionAdmin with verify/unverify actions
    │   └── migrations/
    │
    ├── events/                        The curated content and its taxonomies
    │   ├── models.py                    SchoolLevel, Category, Event (+ EventQuerySet.visible_to),
    │   │                                  EventCategory through table, SavedEvent
    │   ├── filters.py                     ?category=&school_level=&institution=&is_virtual=
    │   │                                  &start_after=&start_before=&upcoming=&search=
    │   ├── serializers.py                  EventSerializer (read) vs EventWriteSerializer
    │   │                                    (dates, virtual/physical contradictions, ownership)
    │   ├── services.py                      create/update/delete/verify event, save/unsave —
    │   │                                     transactional, audited, storage-aware
    │   ├── views.py                          Event list/detail/verify/save, saved-event list,
    │   │                                     per-event registration list, category + level lists
    │   ├── urls.py                            Routes under /api/events/, /api/categories/,
    │   │                                       /api/school-levels/, /api/users/me/saved-events/
    │   ├── admin.py                            EventAdmin (+ verify action), Category, SchoolLevel,
    │   │                                       SavedEvent admins
    │   └── migrations/
    │
    ├── registrations/                  A student's registration for an event
    │   ├── models.py                     EventRegistration (unique per user+event, status)
    │   ├── services.py                    register_for_event (locks the event row, re-checks it,
    │   │                                   reactivates cancelled rows), cancel, set status
    │   ├── serializers.py                  Read + create + status-change serializers
    │   ├── views.py                          Create, own list, detail, cancel, mark attendance
    │   ├── urls.py                            Routes under /api/registrations/ and
    │   │                                       /api/users/me/registrations/
    │   ├── admin.py                            RegistrationAdmin (event, user, status, time)
    │   └── migrations/
    │
    ├── preferences/                     One preference row per user
    │   ├── models.py                      UserPreference (1:1 User, school level, notification
    │   │                                   toggles) + UserPreferenceCategory through table
    │   ├── serializers.py                   Reads nested taxonomies, writes id lists
    │   ├── views.py                           MyPreferenceView — GET/PATCH own row only
    │   ├── urls.py                             Route under /api/preferences/me/
    │   ├── admin.py                             UserPreferenceAdmin with category inline
    │   └── migrations/
    │
    └── recommendations/                   Rule-based ranking for the home feed
        ├── services.py                       build_profile + score_event + recommend_events:
        │                                      category overlap, school-level match, location
        │                                      match, institution match, happening-soon decay.
        │                                      Every point is explained by a named rule and the
        │                                      ordering is deterministic.
        ├── views.py                            RecommendationFeedView — works signed in or out
        └── urls.py                              Route under /api/recommendations/feed/
```

Every `apps/<name>/tests/` folder holds that app's `pytest` tests (happy path,
permission boundaries, edge cases). Run them all with `pytest` from `backend/`.

### 2.1 URL prefix → app cheat-sheet

| URL prefix | Handled by |
|---|---|
| `/api/auth/*` | `apps/users/auth_urls.py` (register, login, token/refresh, logout, csrf) |
| `/api/users/me/`, `/api/users/` | `apps/users/urls.py` (profile, admin account management) |
| `/api/users/me/saved-events/` | `apps/events/urls.py` |
| `/api/users/me/registrations/` | `apps/registrations/urls.py` |
| `/api/institutions/*` | `apps/organizers/urls.py` |
| `/api/events/*`, `/api/categories/`, `/api/school-levels/` | `apps/events/urls.py` |
| `/api/registrations/*` | `apps/registrations/urls.py` |
| `/api/preferences/me/` | `apps/preferences/urls.py` |
| `/api/recommendations/feed/` | `apps/recommendations/urls.py` |
| `/api/admin/activity-logs/` | `apps/common/urls.py` |
| `/admin/*` | Django's built-in admin site |

Full request/response shapes and `curl` examples for every one of these live
in [`API.md`](API.md).

---

## 3. `frontend/` — Vanilla HTML/CSS/JS client

```
frontend/
├── index.html                Home page (the only page not in pages/, so it's the site root)
├── netlify.toml                Netlify deploy config (publish dir, SPA-style redirects)
│
├── pages/                     One .html file per route — pure markup + mount points,
│   │                          no inline logic (that lives in the matching js/pages/*.js)
│   ├── login.html               Log in form
│   ├── register.html             Sign-up form (institution, education level, password)
│   ├── reset-password.html         Two-step "request link" / "set new password" form
│   ├── event-listings.html          Full event grid + filter sidebar (category/location/
│   │                                 education level/fee) + pagination
│   ├── event.html                    Single event detail — expects ?slug=<event-slug>
│   ├── profile.html                   Tabbed account page: "My Profile" tab (this file)
│   ├── preferences.html                Tabbed account page: "Preferences" tab
│   ├── registrations.html               Tabbed account page: "My Registrations" tab
│   └── event-form.html                   Staff-only "Add Event" form (hits the same
│                                            POST /api/events/ a future mobile app would use)
│
├── css/
│   ├── base.css                Design tokens ONLY: CSS custom properties for colour
│   │                            palette (navy/gold/teal), fonts (Inria Serif), spacing,
│   │                            radii, shadows, plus the global reset and the blurred
│   │                            gold "glow blob" background (pure CSS, no image assets)
│   ├── components.css            Reusable pieces used on multiple pages: buttons
│   │                              (.btn-primary/.btn-gold/.btn-secondary), form fields,
│   │                              header/nav, footer, event-card, filter panel, toasts,
│   │                              auth card
│   └── pages.css                  Layout rules specific to one page or page family:
│                                    hero section, category icon row, event-detail layout,
│                                    profile/preferences tabbed card
│
├── js/
│   ├── utils/                       Framework-free helpers, imported by everything else
│   │   ├── config.js                  Single source of truth for API_BASE_URL — auto-
│   │   │                              switches between local Django (127.0.0.1:8000) and
│   │   │                              the deployed Render URL based on hostname
│   │   ├── api.js                      The fetch() wrapper every page uses: always sends
│   │   │                                credentials (cookies), auto-retries once after a
│   │   │                                401 via /auth/token/refresh/, throws a typed
│   │   │                                ApiError with the normalised { message, fields }
│   │   ├── auth.js                       getCurrentUser() (cached per page load),
│   │   │                                 requireAuth() (redirect to login if logged out),
│   │   │                                 clearCurrentUserCache(), initials() helper
│   │   ├── dom.js                         qs/qsa shortcuts, escapeHtml (XSS-safe
│   │   │                                  interpolation), formToObject, getQueryParam,
│   │   │                                  formatDate/formatShortDate/formatTimeRange/formatFee
│   │   └── toast.js                        toast.success()/toast.error() — dependency-free
│   │                                        notification popups
│   │
│   ├── components/                    Reusable pieces of UI shared across every page
│   │   ├── header.js                    renderHeader() — injects the sticky nav (logo,
│   │   │                                search bar, hamburger menu) into #site-header;
│   │   │                                menu contents change based on getCurrentUser()
│   │   ├── footer.js                     renderFooter() — injects the 3-column footer
│   │   │                                 (contact, socials, mailing-list signup) into
│   │   │                                 #site-footer
│   │   └── event-card.js                  createEventCard()/renderEventGrid()/
│   │                                        renderCardSkeletons() — the event card used on
│   │                                        the home feed, listings page, and event page
│   │
│   └── pages/                          One script per route, same name as its .html file.
│       ├── home.js                       Loads the curated feed (GET /recommendations/feed/),
│       │                                 wires the hero search bar, renders category icons
│       ├── login.js                        Submits the login form, redirects home on success
│       ├── register.js                      Submits the register form, surfaces field errors
│       ├── reset-password.js                 Reads ?uid=&token= from the URL to switch
│       │                                     between "request link" and "set new password" steps
│       ├── event-listings.js                  Reads filter query params, calls
│       │                                      GET /events/ with them, renders grid + pagination
│       ├── event.js                            Reads ?slug=, loads one event, wires
│       │                                       follow/unfollow + register buttons, "read more"
│       │                                       description toggle
│       ├── profile.js                            Loads/saves the logged-in user's own profile
│       │                                         fields + avatar upload
│       ├── preferences.js                         Loads/saves the logged-in user's
│       │                                          UserPreference (categories, locations, etc.)
│       ├── registrations.js                       Loads "my registrations" list
│       └── event-form.js                            Staff-only create-event form submission
│
└── assets/
    ├── images/            logo.png, event-cover-default.jpg (placeholder cover), social icons
    └── icons/               Category icons (cat-math.svg, cat-languages.svg, ...) and small
                              UI icons (chevron, search, calendar, location, hamburger, etc.)
```

### 3.1 Page ↔ script ↔ API pairing

| Page (`pages/*.html`) | Script (`js/pages/*.js`) | Main API calls it makes |
|---|---|---|
| `index.html` (root, not in `pages/`) | `home.js` | `GET /recommendations/feed/`, `GET /events/categories/` |
| `login.html` | `login.js` | `POST /auth/login/` |
| `register.html` | `register.js` | `POST /auth/register/` |
| `reset-password.html` | `reset-password.js` | `POST /auth/password-reset/`, `POST /auth/password-reset/confirm/` |
| `event-listings.html` | `event-listings.js` | `GET /events/?category=&location=...` |
| `event.html?slug=...` | `event.js` | `GET /events/{slug}/`, `POST /organizers/{slug}/follow/`, `POST /registrations/` |
| `profile.html` | `profile.js` | `GET/PATCH /users/me/`, `POST /users/me/avatar/` |
| `preferences.html` | `preferences.js` | `GET/PUT /preferences/me/` |
| `registrations.html` | `registrations.js` | `GET /registrations/` |
| `event-form.html` (staff only) | `event-form.js` | `POST /events/` |

---

## 4. `docs/` — documentation set

| File | What's in it |
|---|---|
| `FILE_GUIDE.md` | **This file.** File-by-file map of the whole repo. |
| `ARCHITECTURE.md` | The *why*: tech stack rationale, request-flow walkthroughs, data model diagram, auth design, testing/deployment strategy, future growth path. |
| `SETUP.md` | Step-by-step local dev setup (backend venv, frontend static server, Supabase configuration, common troubleshooting). |
| `API.md` | Every REST endpoint: method, path, auth requirement, request/response JSON, `curl` examples. |
| `DEPLOYMENT.md` | Deploying for free — backend to Render, frontend to Netlify. |

---

## 5. "I want to change X" → start here

| I want to... | Start in... |
|---|---|
| Change a colour, font, spacing, or shadow anywhere on the site | `frontend/css/base.css` (it's all CSS variables — one edit updates every page) |
| Change how a button/input/card/header/footer looks | `frontend/css/components.css` |
| Change one page's unique layout (hero, event-detail grid, profile tabs) | `frontend/css/pages.css` |
| Change what's on a page, or add a new field to a form | The page's `.html` in `frontend/pages/` + its `.js` in `frontend/js/pages/` |
| Change what data an API endpoint returns | The relevant app's `serializers.py` in `backend/apps/<name>/` |
| Change validation rules or business logic (e.g. capacity limits) | The relevant app's `views.py` or `models.py` |
| Add a brand-new field to a model (e.g. `Event.max_age`) | `models.py` → `python manage.py makemigrations` → `migrate` → update `serializers.py` |
| Change how the home feed ranks events | `backend/apps/recommendations/services.py` (`rank_events_for_user`) |
| Add a new API route | `views.py` (new view/action) + wire it in that app's `urls.py` |
| Change login/session behaviour or cookie settings | `backend/apps/users/authentication.py` + `backend/config/settings.py` (`SIMPLE_JWT`, cookie names) |
| Change error message formatting sent to the frontend | `backend/apps/common/exceptions.py` |
| Add demo/sample data for local testing | `backend/apps/events/management/commands/seed_demo_data.py` |
| Swap the local/deployed API URL the frontend calls | `frontend/js/utils/config.js` |
| Add a new icon/image | Drop the file in `frontend/assets/icons/` or `assets/images/`, reference its path from CSS/HTML/JS |
