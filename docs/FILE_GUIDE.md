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
│                               (migrate, runserver, createsuperuser, seed_demo_data, test)
├── requirements.txt            Production Python dependencies (installed on Render)
├── requirements-dev.txt        + pytest, pytest-django, faker — local/dev only
├── pytest.ini                  pytest config (points at config.settings, reuses DB)
├── conftest.py                 Shared pytest fixtures (e.g. an authenticated API client)
├── .env.example                 Template for your own backend/.env (copy, don't edit this one)
├── .env                          Your real local secrets — gitignored, never commit
├── db.sqlite3                    Local dev database file (auto-created, gitignored)
├── Procfile                       Tells Render/Heroku-style hosts how to run gunicorn
├── render.yaml                    Render "infra as code" — declares the web service + env vars
│
├── config/                        The Django "project" — global settings, not a feature
│   ├── settings.py                 THE file for config: installed apps, DB connection,
│   │                                CORS_ALLOWED_ORIGINS, JWT lifetimes/cookie names,
│   │                                Supabase env vars, static/media paths
│   ├── urls.py                      Root URL router — maps /api/<app>/ prefixes to each
│   │                                app's own urls.py (see the table below)
│   ├── wsgi.py                      Entrypoint gunicorn uses in production (via Procfile)
│   └── asgi.py                      Async entrypoint (present for completeness; unused for now)
│
└── apps/                          One Django "app" (folder) per feature area
    ├── common/                     Shared code with no database models of its own
    │   ├── exceptions.py            Normalises every API error into one JSON shape:
    │   │                            { "error": { "message": "...", "fields": {...}|null } }
    │   ├── permissions.py            IsStaffOrReadOnly (events/organizers are curated, not
    │   │                              user-generated) and IsOwner (object-level ownership check)
    │   └── supabase_storage.py        upload_file()/delete_file() against Supabase Storage's
    │                                    REST API — used for avatars + event cover images
    │
    ├── users/                       Accounts, auth, profile
    │   ├── models.py                  Custom User (email as username) + EducationLevel choices
    │   ├── managers.py                 UserManager — create_user()/create_superuser() by email
    │   ├── authentication.py           CookieJWTAuthentication (reads JWT from httpOnly cookie
    │   │                                instead of an Authorization header) + set/clear cookie helpers
    │   ├── tokens.py                    Password-reset token generator (invalidated if email changes)
    │   ├── serializers.py                RegisterSerializer, LoginSerializer, MeSerializer, etc.
    │   ├── views.py                       RegisterView, LoginView, LogoutView, RefreshView,
    │   │                                    PasswordResetRequestView, PasswordResetConfirmView,
    │   │                                    MeView (GET/PATCH own profile), AvatarUploadView
    │   ├── auth_urls.py                    Routes under /api/auth/ (register, login, logout,
    │   │                                    token/refresh, password-reset, password-reset/confirm)
    │   ├── urls.py                          Routes under /api/users/ (me/, me/avatar/)
    │   ├── admin.py                          Registers User in Django admin
    │   └── migrations/                        Database schema history for this app
    │
    ├── organizers/                    Event hosts (schools, clubs) + follow relationships
    │   ├── models.py                    Organizer (name, slug, description, logo) + Follow (user↔organizer)
    │   ├── serializers.py                 OrganizerSerializer (+ follower counts)
    │   ├── views.py                        OrganizerViewSet (CRUD, staff-only writes) with a
    │   │                                    custom follow/unfollow action
    │   ├── urls.py                          Routes under /api/organizers/
    │   ├── admin.py                          Registers Organizer/Follow in Django admin
    │   └── migrations/
    │
    ├── events/                        The core content: categories + events
    │   ├── models.py                    Category (flat taxonomy: Math, Music, Volleyball...),
    │   │                                  EventStatus choices, Event (title, organizer FK,
    │   │                                  categories M2M, venue, date, fee, capacity, is_featured)
    │   ├── filters.py                     django-filter FilterSet — powers ?category=&location=
    │   │                                  &education_level=&fee=&is_free query params
    │   ├── serializers.py                  EventListSerializer (light, for grids) vs.
    │   │                                    EventDetailSerializer (full, for the event page)
    │   ├── views.py                          CategoryViewSet, EventViewSet (list/retrieve by
    │   │                                     slug, staff-only create/update/delete)
    │   ├── urls.py                            Routes under /api/events/ (+ /api/events/categories/)
    │   ├── admin.py                            Rich admin list (filter/search/bulk "mark featured")
    │   ├── management/commands/seed_demo_data.py   Populates realistic demo organizers/
    │   │                                             categories/events for local testing —
    │   │                                             run with `python manage.py seed_demo_data`
    │   └── migrations/
    │
    ├── registrations/                  A student's RSVP to an event
    │   ├── models.py                     RegistrationStatus choices + Registration (user FK,
    │   │                                  event FK, unique-together, capacity enforcement)
    │   ├── serializers.py                  RegistrationSerializer
    │   ├── views.py                          RegistrationViewSet (create/list own, staff can see all;
    │   │                                     blocks duplicate/over-capacity registrations)
    │   ├── urls.py                            Routes under /api/registrations/
    │   ├── admin.py                            Registers Registration in Django admin
    │   └── migrations/
    │
    ├── preferences/                     A student's interests (drives the home feed)
    │   ├── models.py                      UserPreference (categories M2M, education_levels,
    │   │                                   locations, feed_window_days) — 1:1 with User
    │   ├── serializers.py                   UserPreferenceSerializer
    │   ├── views.py                           MyPreferenceView (GET/PUT own preferences only)
    │   ├── urls.py                             Routes under /api/preferences/ (me/)
    │   ├── admin.py                             Registers UserPreference in Django admin
    │   └── migrations/
    │
    └── recommendations/                   Rule-based curation for the home feed
        ├── services.py                       rank_events_for_user() — the one function that
        │                                      scores/sorts events (category overlap, location
        │                                      match, education-level match, followed-organizer
        │                                      boost, featured boost, "happening soon" boost);
        │                                      swap this out later for real ML without touching
        │                                      views/serializers/frontend
        ├── views.py                            FeedView — GET /api/recommendations/feed/
        └── urls.py                              Routes under /api/recommendations/
```

Every `apps/<name>/tests/` folder holds that app's `pytest` tests (happy path,
permission boundaries, edge cases). Run them all with `pytest` from `backend/`.

### 2.1 URL prefix → app cheat-sheet

| URL prefix | Handled by | 
|---|---|
| `/api/auth/*` | `apps/users/auth_urls.py` (register, login, logout, refresh, password reset) |
| `/api/users/*` | `apps/users/urls.py` (`me/`, `me/avatar/`) |
| `/api/organizers/*` | `apps/organizers/urls.py` |
| `/api/events/*` | `apps/events/urls.py` (+ nested `categories/`) |
| `/api/registrations/*` | `apps/registrations/urls.py` |
| `/api/preferences/*` | `apps/preferences/urls.py` (`me/`) |
| `/api/recommendations/*` | `apps/recommendations/urls.py` (`feed/`) |
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
