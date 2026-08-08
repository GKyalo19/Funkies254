# Funkies254 — Software Architecture

Funkies254 is a platform where Kenyan high school and college students discover student
events (academic competitions, sports tournaments, social events) happening in — and
eventually outside — Kenya. This document explains **what** the system is made of,
**why** each piece was chosen, and **how** the pieces talk to each other.

---

## 1. High-level overview

```
┌─────────────────────┐        HTTPS + JSON        ┌──────────────────────┐
│   Frontend (SPA-ish) │ ─────────────────────────▶ │   Backend REST API   │
│  Vanilla HTML/CSS/JS │ ◀───────────────────────── │   Django + DRF       │
│  Hosted on Netlify   │      httpOnly JWT cookies   │   Hosted on Render   │
└─────────────────────┘                              └──────────┬───────────┘
                                                                  │
                                                     SQL (psycopg2) + Storage REST API
                                                                  │
                                                       ┌──────────▼───────────┐
                                                       │       Supabase       │
                                                       │  Postgres + Storage  │
                                                       │ (events, users, ...  │
                                                       │  cover images, etc.) │
                                                       └───────────────────────┘
```

- **Frontend**: static HTML/CSS/JS, no build step, no framework. Talks to the backend
  exclusively over `fetch()` calls to a JSON REST API.
- **Backend**: a Django project exposing a REST API (via Django REST Framework). Owns
  all business logic — auth, event curation, registrations, recommendations.
- **Database**: PostgreSQL, hosted for free on Supabase. Also provides free object
  storage for event cover images and user avatars.

This is a classic **decoupled frontend/backend** architecture. The two halves can be
developed, tested, deployed, and scaled independently, and either could be swapped later
(e.g. replacing the vanilla frontend with a React Native mobile app) without touching the
other side, because they only ever communicate through the documented REST API (see
`docs/API.md`).

---

## 2. Why these technology choices

| Layer | Choice | Why |
|---|---|---|
| Frontend | Vanilla HTML/CSS/JS (ES modules) | No build tooling to learn/maintain, loads instantly, easy to host for free, and is enough for the current scope (a handful of pages, no complex client-side state). |
| Backend language/framework | Python + Django + Django REST Framework | Django's admin panel gives free content curation tooling from day one (mark events featured, moderate organizers) without building custom admin UI. Python has the richest ecosystem (pandas, scikit-learn) to grow the recommendation engine into real ML later, without a language rewrite. |
| Auth | JWT in httpOnly cookies | Stateless (no server-side session store needed, which matters on a free-tier host that may restart/scale to zero), and httpOnly cookies can't be read by JavaScript, which protects tokens from XSS — a real concern in a vanilla-JS app with no framework sanitising output for you. |
| Database | PostgreSQL via Supabase | Relational data (events ↔ categories ↔ organizers ↔ registrations ↔ users) is naturally modeled with foreign keys and joins. Supabase's free tier bundles Postgres *and* object storage (for images/videos) behind one dashboard, which is simpler to manage solo than juggling two separate services. |
| Hosting | Netlify (frontend) + Render (backend) | Both have generous, genuinely free tiers with automatic HTTPS and git-based deploys — no credit card required to start. |

---

## 3. Backend architecture (Django)

### 3.1 Project layout

```
backend/
├── manage.py
├── requirements.txt              # production dependencies
├── requirements-dev.txt          # + pytest, faker, etc. for local dev
├── .env.example                  # template for backend/.env (never committed)
├── config/                       # Django "project" — settings & root URLs
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py                   # entrypoint gunicorn uses on Render
│   └── asgi.py
└── apps/                         # Django "apps" — one folder per bounded concern
    ├── common/                   # shared code with no models of its own
    │   ├── exceptions.py         #   -> one predictable JSON error shape
    │   ├── permissions.py        #   -> reusable DRF permission classes
    │   └── supabase_storage.py   #   -> upload/delete files in Supabase Storage
    ├── users/                    # custom User model + auth endpoints
    ├── organizers/               # event hosts (schools, clubs) + follows
    ├── events/                   # Category + Event models, the core content
    ├── registrations/            # a student's RSVP to an event
    ├── preferences/              # a student's interests, feeds the recommender
    └── recommendations/          # rule-based curation logic for the home feed
```

Each app under `apps/` follows the same internal shape:

```
apps/<name>/
├── models.py       # database tables
├── serializers.py   # how models convert to/from JSON
├── views.py         # request handling (DRF ViewSets/APIViews)
├── urls.py           # this app's routes, included by config/urls.py
├── admin.py           # how this app appears in /admin/
├── apps.py             # Django app config (sets the app's short "label")
├── migrations/          # generated database schema history
└── tests/                # pytest tests scoped to this app
```

This "one app per concern" structure means you can reason about (and test) `events`
without needing to understand `registrations` or `recommendations` — each app only
imports from another app's `models.py`/`serializers.py` when it genuinely needs to
reference that data (e.g. `registrations` imports `events.Event`).

### 3.2 Request flow (example: loading the home feed)

1. Browser calls `GET /api/recommendations/feed/` with the `f254_access` cookie attached
   automatically (browsers send cookies same-origin/CORS-approved automatically).
2. Django's `CorsMiddleware` confirms the request's `Origin` is in
   `CORS_ALLOWED_ORIGINS` and allows credentials through.
3. `apps.users.authentication.CookieJWTAuthentication` reads the JWT from the cookie
   (instead of an `Authorization` header) and attaches `request.user`.
4. `apps.recommendations.views.FeedView` calls `apps.recommendations.services.rank_events_for_user()`,
   which:
   - Pulls a pool of upcoming, published events.
   - Scores each one using the user's saved `UserPreference` (category overlap,
     location match, education level match), boosts events from organizers they
     follow, boosts curator-marked `is_featured` events, and gives a small
     "happening soon" bonus.
   - Falls back to "featured, then soonest" for anonymous visitors or students who
     haven't set preferences yet.
5. The ranked events are serialized with `EventListSerializer` and returned as JSON.
6. The frontend's `js/pages/home.js` renders them into event cards.

### 3.3 Authentication design

- Users are modeled by a **custom `User`** (in `apps/users/models.py`) keyed by
  **email**, not a separate username — matches how the Figma designs collect login
  info.
- On register/login, the backend issues a SimpleJWT access + refresh token pair and
  sets them as **httpOnly, `SameSite` cookies** (see `apps/users/authentication.py`)
  instead of returning them in the JSON body. JavaScript can never read these cookies
  (mitigates XSS token theft); the browser attaches them automatically on every request.
- When an access token expires (30 min), the frontend's `js/utils/api.js` automatically
  calls `POST /api/auth/token/refresh/` once and retries the original request — the user
  never notices, as long as their refresh token (14 days) is still valid.
- **Why not `Authorization: Bearer` headers?** That would require storing the token in
  `localStorage`/`sessionStorage`, which *is* readable by any injected script — a bigger
  risk in a framework-less frontend where there's no built-in output sanitisation.

### 3.4 Curation & recommendations

Event content is **curated, not user-generated** by design — regular students can read
events but never create/edit them (`apps.common.permissions.IsStaffOrReadOnly`). Staff
accounts (created via `createsuperuser` or promoted in `/admin/`) can:

- Add/edit events and organizers directly in the polished Django admin (bulk actions,
  filtering, search — all free, out of the box), **or**
- Use the lightweight `frontend/pages/event-form.html` page, which exercises the same
  `POST /api/events/` API a mobile app would eventually use.

The recommendation engine (`apps/recommendations/services.py`) is a transparent,
**rule-based scoring function** on purpose, not a machine learning model — at launch
there isn't yet enough interaction data (views, click-throughs, past registrations) to
train anything meaningful, and a rule-based system is far easier to debug ("why is this
event showing?") and to explain to users. The function's *public contract* — "give me a
ranked list of events for this user" — is exactly what a real ML model would also expose,
so swapping in collaborative filtering (e.g. via `scikit-learn` or `implicit`) later is an
internal change to one file, not an API redesign.

### 3.5 Media storage (Supabase Storage)

Event cover images and user avatars are **never stored on the backend's local disk** —
free hosts like Render use ephemeral filesystems that wipe on every redeploy. Instead,
`apps/common/supabase_storage.py` uploads files directly to a Supabase Storage bucket via
its REST API and stores only the resulting **public URL** on the `Event`/`User` row.
This also means the API server itself stays lightweight (no need to serve large files).

---

## 4. Frontend architecture (Vanilla HTML/CSS/JS)

### 4.1 Project layout

```
frontend/
├── index.html                 # Home page
├── pages/                     # one .html file per route
│   ├── login.html
│   ├── register.html
│   ├── reset-password.html
│   ├── event-listings.html
│   ├── event.html             # ?slug=<event-slug>
│   ├── profile.html
│   ├── preferences.html
│   ├── registrations.html     # "My Registrations"
│   └── event-form.html        # staff-only "Add Event"
├── css/
│   ├── base.css                # design tokens (colours, spacing) + resets
│   ├── components.css           # buttons, inputs, cards, header, footer, toast
│   └── pages.css                 # layout rules specific to certain pages
└── js/
    ├── utils/
    │   ├── config.js              # API_BASE_URL (switches local vs. deployed)
    │   ├── api.js                  # fetch() wrapper: cookies, 401 refresh-retry, errors
    │   ├── auth.js                  # getCurrentUser()/requireAuth()/logout() cache
    │   ├── dom.js                    # qs/qsa/escapeHtml/formatters/query params
    │   └── toast.js                   # success/error notifications
    ├── components/
    │   ├── header.js                  # shared nav, injected into every page
    │   ├── footer.js                    # shared footer, injected into every page
    │   └── event-card.js                 # renders one event card (reused everywhere)
    └── pages/
        └── <page-name>.js                 # one script per page, matching the .html file
```

### 4.2 Why no framework/bundler

At this stage the frontend is a handful of largely-independent pages (login, home,
listings, event detail, profile) with modest shared state (mostly just "who is logged
in"). Plain **ES modules** (`<script type="module">`) already give us:

- Real code splitting per page (each page only loads the JS it needs).
- `import`/`export` for sharing `api.js`, `header.js`, etc. without a bundler.
- Zero build step — open the file, refresh the browser, see the change.

If the app grows substantially (many interdependent components, complex client state,
routing without full page reloads), migrating to a framework (React/Vue/Svelte) later is
a frontend-only change — the backend's REST API doesn't need to know or care.

### 4.3 How a page works, end to end (example: the Event page)

1. `pages/event.html` loads shared CSS, has empty mount points
   (`<div id="site-header">`, `<div id="event-content">`, `<div id="site-footer">`),
   and loads `js/pages/event.js` as a module.
2. `event.js` reads `?slug=` from the URL (`getQueryParam`), calls
   `renderHeader()`/`renderFooter()` (which themselves call `getCurrentUser()` to decide
   whether to show "Log in" or an avatar menu), then calls
   `GET /api/events/{slug}/` via `api.js`.
3. The returned event JSON is turned into HTML (organizer card, date/venue info,
   registration card) and injected into `#event-content`.
4. Clicking "Follow" or "Register" makes another `api.js` call
   (`POST /api/organizers/{slug}/follow/`, `POST /api/registrations/`), shows a toast, and
   re-renders the page with fresh data — no page reload needed for those actions.

### 4.4 Design tokens

`css/base.css` defines CSS custom properties (`--color-primary`, `--radius-lg`, spacing
scale, etc.) so the "gold hues" warm theme from the Figma designs stays consistent across
every page. If you pull exact hex values / spacing from Figma later (via
`get_design_context`), only `base.css` needs updating — every component/page references
the same variables.

---

## 5. Data model summary

```
User ──1:1── UserPreference ──M2M── Category ──M2M── Event ──FK── Organizer ──1:M── Follow ──FK── User
  │                                                      │
  └──────────────────1:M────────── Registration ─────────┘
```

| Model | Owning app | Purpose |
|---|---|---|
| `User` | `users` | Email-based account. Includes `institution`, `education_level` (matches Register page). |
| `Organizer` | `organizers` | The host behind an event (school, club, company). Curated by admins. |
| `Follow` | `organizers` | A student following an organizer. |
| `Category` | `events` | Flat taxonomy (Math, Science, Volleyball, ...) shared by events, preferences, and filters. |
| `Event` | `events` | Core content: title, organizer, categories, venue, date, fee, capacity, curation flags. |
| `Registration` | `registrations` | A student's RSVP to an event. Enforces capacity. |
| `UserPreference` | `preferences` | A student's interests — categories, education levels, locations, feed window. Feeds `recommendations`. |

See `docs/API.md` for the exact JSON shape of every model as returned by the API.

---

## 6. Testing strategy

- **Backend**: `pytest` + `pytest-django` (`backend/apps/*/tests/`). Every app has its
  own test file(s) covering the happy path, permission boundaries (anonymous vs. student
  vs. staff), and edge cases (duplicate registration, full capacity, invalid tokens).
  Run with `python manage.py test` or `pytest` from `backend/`.
- **Frontend**: no formal automated test suite yet (would need a browser-automation tool
  like Playwright). In the meantime, `frontend/pages/event-form.html` and the Django
  admin both double as manual API testing tools during development.
- **API testing**: see `docs/API.md` for `curl` examples of every endpoint, and
  `backend/apps/events/management/commands/seed_demo_data.py` to populate realistic
  sample data (`python manage.py seed_demo_data`) before testing manually.

---

## 7. Deployment topology

See `docs/DEPLOYMENT.md` for step-by-step instructions. In short:

- **Backend** → Render (free web service), reading `DATABASE_URL`/`SUPABASE_*`/`SECRET_KEY`
  etc. from Render's environment variable dashboard (never committed to git).
- **Frontend** → Netlify, publishing the `frontend/` folder directly (no build command
  needed since there's no bundler).
- **Database + Storage** → Supabase (already "deployed" the moment you create a project).

---

## 8. Future growth path (why this architecture scales with you)

- **More countries/currencies**: `Event.location`/`registration_fee` are free-form enough
  to extend; a `Country` model can be introduced later without breaking the API contract.
- **Real recommendations**: `apps/recommendations/services.py` has one entrypoint
  (`rank_events_for_user`) — swap its internals for a trained model without touching
  views, serializers, or the frontend.
- **Mobile app**: since the frontend only talks to the backend over documented REST
  endpoints (with cookie-based auth, which does need adapting — a mobile app would use
  `Authorization` headers instead), a React Native/Flutter app can reuse 100% of the
  backend unchanged.
- **Organizer self-service**: today organizers are curated by admins; a future
  "Organizer" role with its own login could be added as a new permission class without
  restructuring the `Event`/`Organizer` models.
