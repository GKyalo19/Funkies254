# Funkies254 — API Reference

Base URL:
- Local: `http://127.0.0.1:8000/api`
- Production: `https://<your-render-service>.onrender.com/api`

## Conventions

- All request/response bodies are JSON, except file uploads (`multipart/form-data`).
- **Auth is cookie-based.** After login/register, the browser automatically stores
  `f254_access` and `f254_refresh` as httpOnly cookies and sends them on every
  subsequent request — you never manually attach a token. When testing with `curl`, use
  `-c cookies.txt -b cookies.txt` to persist cookies between calls (see examples below).
- **Errors** always come back in this shape:

  ```json
  { "error": { "message": "Human-readable summary.", "fields": { "email": ["This field is required."] } } }
  ```
  `fields` is `null` for non-validation errors (permission denied, not found, etc).
- **Pagination**: list endpoints return
  ```json
  { "count": 42, "next": "http://.../api/events/?page=2", "previous": null, "results": [...] }
  ```
  except `/recommendations/feed/`, which returns `{ "count": N, "results": [...] }` (no
  page-based pagination — it's always a ranked top-N list).
- **Permissions legend**: 🌍 anyone · 🔒 logged-in user · 🛠️ staff only.

---

## Auth — `/api/auth/`

### `POST /api/auth/register/` 🌍
Create an account and log in immediately (sets auth cookies).

```json
// Request
{
  "email": "student@example.com",
  "password": "StrongPass123",
  "confirm_password": "StrongPass123",
  "institution": "Mang'u High School",
  "education_level": "high_school"
}
```
`201 Created` → `{ "user": { ...UserSerializer } }`

```bash
curl -c cookies.txt -X POST http://127.0.0.1:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"student@example.com","password":"StrongPass123","confirm_password":"StrongPass123","institution":"Mangu High","education_level":"high_school"}'
```

### `POST /api/auth/login/` 🌍
```json
{ "email": "student@example.com", "password": "StrongPass123" }
```
`200 OK` → `{ "user": {...} }`, sets cookies.

### `POST /api/auth/logout/` 🌍
No body. Clears auth cookies. Always `200 OK`.

### `POST /api/auth/token/refresh/` 🌍
No body — reads the refresh cookie. Issues a new access (+ rotated refresh) cookie pair.
The frontend calls this automatically whenever a request returns 401; you rarely need to
call it manually.

### `POST /api/auth/password-reset/request/` 🌍
```json
{ "email": "student@example.com" }
```
Always `200 OK` (doesn't reveal whether the email exists). In dev, the reset email is
printed to the Django server's console (`EMAIL_BACKEND=console`).

### `POST /api/auth/password-reset/confirm/` 🌍
```json
{ "uid": "<from emailed link>", "token": "<from emailed link>", "new_password": "NewPass456" }
```
`200 OK` on success, `400` if the link is invalid/expired.

---

## Users — `/api/users/`

### `GET /api/users/me/` 🔒
Returns the logged-in user's profile.

```bash
curl -b cookies.txt http://127.0.0.1:8000/api/users/me/
```

### `PATCH /api/users/me/` 🔒
Partial update. Accepts any of `first_name`, `last_name`, `institution`,
`education_level`, `phone_number`. `email` is read-only.

### `POST /api/users/me/avatar/` 🔒
`multipart/form-data` with a field named `avatar`. Uploads to Supabase Storage, returns
the updated user profile.

```bash
curl -b cookies.txt -X POST http://127.0.0.1:8000/api/users/me/avatar/ \
  -F "avatar=@/path/to/photo.jpg"
```

---

## Organizers — `/api/organizers/`

### `GET /api/organizers/` 🌍 · `GET /api/organizers/{slug}/` 🌍
Returns organizer(s) with `followers_count` and (if logged in) `is_following`.

### `POST /api/organizers/` 🛠️ · `PATCH/PUT /api/organizers/{slug}/` 🛠️ · `DELETE /api/organizers/{slug}/` 🛠️
Manage organizers. Fields: `name`, `logo_url`, `description`, `website`,
`contact_email`, `contact_phone`, `years_hosting`.

### `POST /api/organizers/{slug}/follow/` 🔒 · `DELETE /api/organizers/{slug}/follow/` 🔒
Follow / unfollow an organizer. No body needed.

---

## Categories — `/api/events/categories/`

### `GET /api/events/categories/` 🌍
Not paginated — returns the full flat list, e.g.:
```json
[{ "id": 1, "name": "Math", "slug": "math", "icon": "mdi:calculator-variant" }, ...]
```

### `POST /api/events/categories/` 🛠️ · `PATCH/DELETE /api/events/categories/{id}/` 🛠️

---

## Events — `/api/events/`

### `GET /api/events/` 🌍
Filterable, searchable, paginated list. Query params:

| Param | Example | Meaning |
|---|---|---|
| `category` | `?category=math` | Category slug (exact match) |
| `location` | `?location=Nairobi` | Case-insensitive contains |
| `education_level` | `?education_level=high_school` | `high_school` \| `college` \| `both` |
| `date_from` / `date_to` | `?date_from=2026-08-01T00:00:00Z` | ISO datetime bounds on `start_datetime` |
| `fee` | `?fee=free` or `?fee=paid` | Free (`0`) vs. paid events |
| `is_featured` | `?is_featured=true` | Curator-boosted events |
| `search` | `?search=math+olympiad` | Full-text-ish search across title/description/venue/location |
| `ordering` | `?ordering=-start_datetime` | Any of `start_datetime`, `registration_fee`, `created_at` (prefix `-` for descending) |
| `page` | `?page=2` | Pagination (12 per page by default) |

Non-staff users only ever see `status=published` events, regardless of filters.

```bash
curl "http://127.0.0.1:8000/api/events/?category=math&fee=free&page=1"
```

### `GET /api/events/{slug}/` 🌍
Full event detail — includes `organizer` (nested), `spots_left`,
`registrations_count`, `description`, etc. See `EventDetailSerializer`.

### `GET /api/events/{slug}/similar/` 🌍
Up to 6 other published, upcoming events sharing a category with this one.

### `POST /api/events/` 🛠️
```json
{
  "title": "64th Annual Math Olympiad",
  "organizer": 1,
  "categories": [1],
  "description": "...",
  "venue_name": "Mang'u High School",
  "location": "Thika",
  "education_level": "high_school",
  "start_datetime": "2026-08-01T09:00:00Z",
  "registration_fee": "0.00",
  "capacity": 200,
  "is_featured": false,
  "status": "published"
}
```

### `PATCH/PUT /api/events/{slug}/` 🛠️ · `DELETE /api/events/{slug}/` 🛠️

### `POST /api/events/{slug}/cover-image/` 🛠️
`multipart/form-data`, field `cover_image`. Uploads to Supabase Storage.

---

## Registrations — `/api/registrations/`

### `GET /api/registrations/` 🔒
Only ever returns the logged-in user's own registrations (including cancelled ones —
filter client-side on `status` if you only want active ones).

### `POST /api/registrations/` 🔒
```json
{ "event_slug": "64th-annual-math-olympiad" }
```
`201 Created`. Registering twice for the same event updates the existing row instead of
erroring. Fails with `400` if the event is past, unpublished, or fully booked
(`capacity` reached).

### `DELETE /api/registrations/{id}/` 🔒
Cancels (soft-delete — marks `status="cancelled"`, doesn't remove the row).
`204 No Content`.

---

## Preferences — `/api/preferences/`

### `GET /api/preferences/me/` 🔒
Auto-creates a default preference row on first access
(`education_levels: []`, `categories: []`, `preferred_locations: []`, `max_days_ahead: 30`).

### `PATCH /api/preferences/me/` 🔒
```json
{
  "categories": [1, 4],
  "education_levels": ["high_school"],
  "preferred_locations": ["Nairobi", "Thika"],
  "max_days_ahead": 30
}
```

---

## Recommendations — `/api/recommendations/`

### `GET /api/recommendations/feed/?limit=20` 🌍
The Home Page feed. Works for anonymous visitors (falls back to featured + soonest
events); personalised for logged-in users based on their saved preferences, followed
organizers, and curator `is_featured` flags. See `docs/ARCHITECTURE.md` §3.4 for how
scoring works. `limit` defaults to 20, capped at 50.

```json
{ "count": 9, "results": [ { "id": 3, "title": "...", ... } ] }
```

---

## Quick end-to-end `curl` test script

```bash
BASE=http://127.0.0.1:8000/api

# Register + capture cookies
curl -s -c cookies.txt -X POST $BASE/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"DemoPass123","confirm_password":"DemoPass123","institution":"Demo School","education_level":"high_school"}'

# Confirm we're logged in
curl -s -b cookies.txt $BASE/users/me/

# Browse events
curl -s "$BASE/events/?page=1" | python3 -m json.tool | head -40

# Register for the first event returned above (replace <slug>)
curl -s -b cookies.txt -X POST $BASE/registrations/ \
  -H "Content-Type: application/json" -d '{"event_slug":"<slug>"}'

# See personalised feed
curl -s -b cookies.txt "$BASE/recommendations/feed/"

# Log out
curl -s -b cookies.txt -X POST $BASE/auth/logout/
```
