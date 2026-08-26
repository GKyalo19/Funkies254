# Funkies254 API Reference

Base URL (local): `http://127.0.0.1:8000`
Base URL (production): `https://<your-service>.onrender.com`

All requests and responses are JSON unless a file upload is involved, in which
case use `multipart/form-data`.

A ready-to-import Postman collection lives at
[`Funkies254.postman_collection.json`](Funkies254.postman_collection.json).

---

## 1. Authentication model

Authentication is a Django-issued JWT pair carried in **httpOnly cookies**:

| Cookie | Contents | Lifetime |
|---|---|---|
| `funkies_access` | Access token | 30 minutes |
| `funkies_refresh` | Refresh token | 14 days |

- Tokens are **never** returned in a response body, so frontend JavaScript
  cannot read them.
- `POST /api/auth/login/` and `POST /api/auth/register/` set both cookies.
- Postman stores and replays these cookies automatically — log in once and every
  later request in the collection is authenticated.
- An `Authorization: Bearer <token>` header is also accepted, which is useful
  for server-to-server calls.
- When `JWT_COOKIE_CSRF_ENFORCED=True` (the production default), any unsafe
  request authenticated by cookie must also send an `X-CSRFToken` header whose
  value comes from `GET /api/auth/csrf/` or the `csrf_token` field returned by
  login. Keep it `False` for local Postman work.

### Roles

| Role | Can |
|---|---|
| `student` | View events, save, register, edit own profile, manage own preferences |
| `institution_staff` | Create events, edit own events, view registrations for own events, update own institution |
| `admin` | View all users/institutions/events, verify institutions and events, suspend users, curate content |
| `super_admin` | Everything, plus creating and removing admins |

Registration always creates a `student`. Elevated roles are granted by an
administrator through `POST /api/users/{id}/role/` or the Django admin.

---

## 2. Error format

Every error uses one envelope:

```json
{
  "detail": "end_time: End time must be after the start time.",
  "code": "invalid",
  "errors": {
    "end_time": ["End time must be after the start time."]
  }
}
```

`errors` is present only for field validation failures.

| Status | Meaning |
|---|---|
| 400 | Validation or business-rule failure |
| 401 | Missing, expired or invalid credentials |
| 403 | Authenticated but not allowed (role or ownership) |
| 404 | Not found, or not visible to you |
| 409 | Conflict (duplicate registration, already cancelled) |
| 502 | Media storage unavailable |

Paginated list responses look like:

```json
{ "count": 42, "next": "...?page=2", "previous": null, "results": [ ... ] }
```

Use `?page=` and `?page_size=` (max 100). `/api/categories/` and
`/api/school-levels/` are unpaginated.

---

## 3. Auth endpoints

### `POST /api/auth/register/` — public

```json
{
  "email": "amina@example.com",
  "name": "Amina Wanjiru",
  "password": "StrongPass!2026",
  "password_confirm": "StrongPass!2026",
  "institution_id": "9f1c...  (optional)"
}
```

`201 Created` — the account is created unverified and **does not** set auth
cookies yet. A 6-digit code is emailed to the address. The frontend should
send the user to the verify-email screen:

```json
{
  "detail": "Account created. Enter the verification code we sent to your email.",
  "email": "amina@example.com",
  "email_verified": false
}
```

Emails are lowercased before storage, so logins are case-insensitive.

### `POST /api/auth/verify-email/` — public

```json
{ "email": "amina@example.com", "code": "482913" }
```

`200 OK` with the same body shape as login (user + `csrf_token`) and sets both
cookies. `400` if the code is wrong, expired, or too many attempts have been
made (`code: invalid_verification_code` / `expired_verification_code` /
`too_many_verification_attempts`).

### `POST /api/auth/resend-verification/` — public

```json
{ "email": "amina@example.com" }
```

Always `200` with a generic message so callers cannot probe whether an email
is registered. A new code is only actually sent when the account exists and
is still unverified. `400` if a code was requested less than 60 seconds ago.

### `POST /api/auth/login/` — public

```json
{ "email": "amina@example.com", "password": "StrongPass!2026" }
```

`200 OK` with the user object (including `email_verified`) and both cookies.
`401` for bad credentials (`code: invalid_credentials`) and for suspended
accounts (`code: account_suspended`). `403` with `code: email_not_verified`
if the password is correct but the address has not been confirmed yet.

### `POST /api/auth/token/refresh/` — public

No body needed; the refresh cookie is used. The refresh token is rotated and
the old one blacklisted. `200 OK` sets fresh cookies. `401` if the cookie is
missing, expired, blacklisted, or the account is no longer active.

### `POST /api/auth/logout/`

Clears both cookies and blacklists the refresh token. Always `200`.

### `GET /api/auth/csrf/` — public

Returns `{"csrf_token": "…"}` and sets the `csrftoken` cookie.

---

## 4. Users

### `GET /api/users/me/` — authenticated

Returns the profile object shown above.

### `PATCH /api/users/me/` — authenticated

Writable: `name`, `avatar` (file upload), and `institution_id` (students only —
staff ownership is derived from that field, so only an admin may change it for
non-students). `email`, `role`, `is_active` and `is_staff` are read-only here.

```bash
curl -X PATCH http://127.0.0.1:8000/api/users/me/ \
  -b cookies.txt -F "name=Amina W." -F "avatar=@avatar.png"
```

### `GET /api/users/` — admin

Filters: `?role=`, `?is_active=`, `?institution=`, `?search=` (email or name),
`?ordering=created_at|email|name|role`.

### `POST /api/users/{id}/suspend/` — admin

Sets `is_active=false`; the account can no longer authenticate and existing
tokens stop working. Writes a `suspended_user` audit record. An admin cannot
suspend themselves or another administrator (super admin only).

### `POST /api/users/{id}/reinstate/` — admin

Reverses a suspension and writes `reinstated_user`.

### `POST /api/users/{id}/role/` — admin (super admin for admin roles)

```json
{ "role": "institution_staff" }
```

Granting or removing `admin`/`super_admin` requires `super_admin`, and logs
`created_admin` or `removed_admin`; other changes log `promoted_user`.
`is_staff`/`is_superuser` are kept in step with the application role.

---

## 5. Preferences

### `GET /api/preferences/me/` — authenticated

```json
{
  "id": "5b2e...",
  "school_level": { "id": "…", "name": "Senior Secondary", "slug": "senior-secondary" },
  "email_notifications": true,
  "push_notifications": false,
  "preferred_categories": [ { "id": "…", "name": "Math", "slug": "math" } ]
}
```

### `PATCH /api/preferences/me/` — authenticated

```json
{
  "school_level_id": "…",
  "email_notifications": false,
  "push_notifications": true,
  "preferred_category_ids": ["…", "…"]
}
```

`preferred_category_ids` replaces the whole selection.

---

## 6. Reference data

### `GET /api/categories/` — public

`[{ "id": "…", "name": "Sports", "slug": "sports" }, …]`

### `GET /api/school-levels/` — public

`[{ "id": "…", "name": "College", "slug": "college" }, …]`

---

## 7. Institutions

### `GET /api/institutions/` — public

Filters: `?verified=true`, `?search=`, `?ordering=name|created_at`.

### `GET /api/institutions/{slug}/` — public

```json
{
  "id": "…",
  "name": "Nairobi High School",
  "slug": "nairobi-high-school",
  "email": "events@nairobihigh.ac.ke",
  "phone": "+254700000001",
  "logo_url": null,
  "location": "Ngara, Nairobi",
  "website": "https://nairobihigh.ac.ke",
  "verified": true,
  "created_by": { "id": "…", "name": "Faith Kamau", "email": "…", "role": "admin", "avatar_url": null },
  "event_count": 4,
  "created_at": "…",
  "updated_at": "…"
}
```

### `POST /api/institutions/` — admin

`{ "name": "Kisumu Girls High School", "location": "Kisumu", "email": "...", "phone": "...", "website": "..." }`

The slug is generated from the name (collisions get a numeric suffix) and
`verified` starts as `false`.

### `PATCH /api/institutions/{slug}/` — owning staff or admin

Institution staff may edit only their own institution. `slug` and `verified`
are read-only here.

### `POST /api/institutions/{slug}/verify/` — admin

Optional body `{ "verified": false }` to withdraw verification. Logs
`verified_institution`.

---

## 8. Events

Events are curated: students never create them.

### `GET /api/events/` — public

Anonymous visitors and students see verified events only. Institution staff
additionally see their own institution's unverified drafts; admins see
everything.

| Parameter | Example |
|---|---|
| `category` | `?category=sports&category=math` (slugs, repeatable) |
| `school_level` | `?school_level=college` |
| `institution` | `?institution=<uuid>` |
| `institution_slug` | `?institution_slug=nairobi-high-school` |
| `is_virtual` | `?is_virtual=true` |
| `is_verified` | `?is_verified=false` (staff/admin views) |
| `start_after` / `start_before` | `?start_after=2026-09-01T00:00:00Z` |
| `upcoming` | `?upcoming=true` hides events that already ended |
| `search` | `?search=chess` (title, description, venue, location) |
| `mine` | `?mine=true` restricts to events you created |
| `ordering` | `?ordering=-start_time` |

### `GET /api/events/{slug}/` — public

`{slug}` also accepts the event UUID.

```json
{
  "id": "…",
  "title": "Nairobi Inter-School Math Olympiad",
  "slug": "nairobi-inter-school-math-olympiad",
  "description": "…",
  "institution": { "id": "…", "name": "Nairobi High School", "slug": "…", "logo_url": null, "location": "Ngara, Nairobi", "verified": true },
  "start_time": "2026-08-31T08:00:00Z",
  "end_time": "2026-08-31T14:00:00Z",
  "venue": "Main Hall",
  "location": "Ngara, Nairobi",
  "latitude": null,
  "longitude": null,
  "school_level": { "id": "…", "name": "Senior Secondary", "slug": "senior-secondary" },
  "categories": [ { "id": "…", "name": "Math", "slug": "math" } ],
  "cover_image_url": null,
  "registration_link": null,
  "is_verified": true,
  "verified_by": null,
  "verified_at": null,
  "is_virtual": false,
  "created_by": { "id": "…", "name": "Brian Otieno", "email": "…", "role": "institution_staff", "avatar_url": null },
  "is_saved": false,
  "is_registered": false,
  "registration_count": 3,
  "created_at": "…",
  "updated_at": "…"
}
```

### `POST /api/events/` — institution staff or admin

```json
{
  "title": "County Chess Championship",
  "description": "Knockout chess tournament for secondary students.",
  "institution_id": "…",
  "start_time": "2026-09-20T08:00:00Z",
  "end_time": "2026-09-20T16:00:00Z",
  "venue": "School Library",
  "location": "Ngara, Nairobi",
  "latitude": null,
  "longitude": null,
  "school_level_id": "…",
  "category_ids": ["…"],
  "registration_link": null,
  "is_virtual": false
}
```

Send as `multipart/form-data` with a `cover_image` file to upload a cover to
Supabase Storage in the same request. `cover_image_url` may also be set
directly.

Validation:

- `end_time` must be after `start_time` (also a database CHECK constraint).
- Latitude within ±90, longitude within ±180 (serializer and CHECK constraint).
- A virtual event may not carry `venue`, `latitude` or `longitude`, and needs a
  `registration_link`.
- Institution staff may only attach events to their own institution; omitting
  `institution_id` fills in theirs automatically.

Events created by staff start unverified and wait for admin review; events
created by an admin are verified immediately. Logs `created_event`.

### `PATCH /api/events/{slug}/` — owning staff or admin

Same payload, all fields optional. `category_ids` replaces the category set.
Logs `updated_event`.

### `DELETE /api/events/{slug}/` — owning staff or admin

`204 No Content`. The audit record (`deleted_event`) survives the deletion, and
the cover image is removed from storage after the transaction commits.

### `POST /api/events/{id}/verify/` — admin

Optional body `{ "verified": false }`. Sets `verified_by`/`verified_at` and
logs `verified_event`. The first time an event is verified, students whose
saved categories (and optional school level) overlap the event — and who have
`email_notifications` on — receive a match email.

### `GET /api/events/{id}/registrations/` — owning staff or admin

Paginated registrations for that event, each with the student attached.

---

## 9. Saved events

### `POST /api/events/{id}/save/` — student

`201` on the first save, `200` with `"already_saved": true` if it was already
saved. Uniqueness is enforced by a database constraint.

```json
{ "saved": true, "already_saved": false, "event_id": "…", "saved_at": "…" }
```

### `DELETE /api/events/{id}/save/` — student

`{ "saved": false, "was_saved": true }`

### `GET /api/users/me/saved-events/` — authenticated

```json
{ "count": 1, "next": null, "previous": null,
  "results": [ { "id": "…", "event": { … }, "saved_at": "…" } ] }
```

---

## 10. Registrations

### `POST /api/registrations/` — student

```json
{ "event_id": "…" }
```

or `{ "event_slug": "county-chess-championship" }`.

`201` on a new registration, `200` if a previously cancelled registration was
reactivated, `409` if you are already registered, `400` if the event is
unverified or has already ended. A confirmation email is sent after a
successful register or reactivation. The event row is locked for the duration of
the transaction, and the unique `(user, event)` constraint is the final guard
against races.

```json
{
  "id": "…",
  "user": { "id": "…", "name": "Amina Wanjiru", "email": "…", "role": "student", "avatar_url": null },
  "event": { … },
  "status": "registered",
  "registered_at": "…"
}
```

### `GET /api/users/me/registrations/` — authenticated

Filter with `?status=registered|attended|cancelled`.

### `GET /api/registrations/{id}/` — owner, event owner or admin

### `POST /api/registrations/{id}/cancel/` — the registered student

Sets `status=cancelled`. `409` if it is already cancelled, `404` if the
registration is not yours.

### `POST /api/registrations/{id}/status/` — event owner or admin

```json
{ "status": "attended" }
```

---

## 11. Recommendations

### `GET /api/recommendations/feed/` — public or authenticated

`?limit=` (default 20, max 50).

```json
{
  "count": 3,
  "personalised": true,
  "results": [
    {
      "score": 7.7,
      "reasons": [
        { "rule": "category_overlap", "points": 3.0, "detail": "Matches your interests: chess." },
        { "rule": "school_level_match", "points": 2.5, "detail": "Targets your school level." },
        { "rule": "location_match", "points": 2.0, "detail": "Happening near you." }
      ],
      "event": { … }
    }
  ]
}
```

Rules and weights: category overlap (3.0 each, capped at 9.0), school-level
match (2.5), location match (2.0), own-institution match (1.5) and a
happening-soon boost that decays from 1.0 to 0 over 14 days. Anonymous visitors
get the soonest upcoming verified events with `personalised: false`. Ranking is
deterministic: ties break on start time, then event id.

---

## 12. Admin activity log

### `GET /api/admin/activity-logs/` — admin

Filters: `?action=`, `?table_name=`, `?record_id=`, `?user=`,
`?ordering=-created_at`.

```json
{
  "id": "…",
  "actor": { "id": "…", "name": "Faith Kamau", "email": "…", "role": "admin" },
  "action": "verified_institution",
  "table_name": "institutions",
  "record_id": "…",
  "created_at": "…"
}
```

Actions: `created_event`, `updated_event`, `deleted_event`, `verified_event`,
`created_institution`, `updated_institution`, `verified_institution`,
`promoted_user`, `suspended_user`, `reinstated_user`, `created_admin`,
`removed_admin`.

---

## 13. Health

### `GET /api/health/` — public

`{ "status": "ok", "service": "funkies254-api" }`

---

## 14. Postman quick start

1. `python manage.py seed_demo_data` — creates demo accounts, all with the
   password `Funkies254!`:

   | Email | Role |
   |---|---|
   | `student@funkies254.test` | student |
   | `staff@funkies254.test` | institution_staff |
   | `admin@funkies254.test` | admin |
   | `superadmin@funkies254.test` | super_admin |

2. `python manage.py runserver`
3. Import `docs/Funkies254.postman_collection.json`.
4. Run **Auth → Login (student)**. Postman keeps the cookies, so every later
   request is authenticated. Log in as a different account to switch roles.
