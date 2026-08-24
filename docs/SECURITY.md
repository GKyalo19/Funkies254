# Funkies254 Security Notes

Django is the application authority. The frontend never talks to PostgreSQL or
Supabase Storage directly, and no Supabase credential ever reaches the browser.

---

## 1. Authentication

- Custom `User` model on `AbstractBaseUser` + `PermissionsMixin`, with `email`
  as `USERNAME_FIELD`. Emails are lowercased before storage so logins are
  case-insensitive and cannot be duplicated by casing.
- Passwords use Django's hashing (PBKDF2 by default) and are validated against
  Django's validators with an 8-character minimum. There is no plaintext
  password column anywhere in the schema.
- SimpleJWT issues the tokens: access 30 minutes, refresh 14 days, rotation on
  every refresh with the old token blacklisted (`token_blacklist` app).
- `role` carries application semantics; `is_staff`/`is_superuser` carry Django
  admin semantics. `change_user_role` keeps them consistent so a demoted admin
  also loses Django admin access.
- Suspension is `is_active=False`. `ModelBackend` refuses to authenticate
  inactive accounts, and `JWTAuthentication` rejects existing tokens for them,
  so a suspension takes effect immediately rather than at token expiry.

## 2. Cookies

| Setting | Local development | Production |
|---|---|---|
| `httpOnly` | `True` | `True` |
| `Secure` | `False` (plain http) | `True` |
| `SameSite` | `Lax` | `None` |
| CSRF enforcement | off (`JWT_COOKIE_CSRF_ENFORCED=False`) | on |

Netlify and Render are different sites, so production cookies must be
`SameSite=None; Secure` for the browser to send them at all. `SameSite=None`
without `Secure` is rejected by browsers — the two settings move together.

Tokens are never included in a response body, so JavaScript cannot read them
even if an XSS bug slips through.

## 3. CSRF

Cookies are attached by the browser automatically, which is exactly what makes
cookie authentication vulnerable to cross-site request forgery. So:

- `CookieJWTAuthentication` runs Django's CSRF check on every unsafe request
  whose credential came from a cookie. Requests authenticated by an
  `Authorization` header are exempt, because the browser will not attach that
  header on its own.
- The check is gated by `JWT_COOKIE_CSRF_ENFORCED` so local Postman testing is
  frictionless. **Set it to `True` in production.**
- The frontend gets its token from `GET /api/auth/csrf/`, or from the
  `csrf_token` field returned by login and register, and echoes it back in the
  `X-CSRFToken` header.
- `CSRF_COOKIE_HTTPONLY = False` on purpose: the frontend must read that cookie.
  It contains no credential.

## 4. CORS

- `CORS_ALLOWED_ORIGINS` is an explicit allowlist from the environment. There is
  no wildcard, because `CORS_ALLOW_CREDENTIALS = True` and wildcards are
  incompatible with credentialed requests.
- `CSRF_TRUSTED_ORIGINS` defaults to the same list.
- Add the exact Netlify origin (scheme + host, no trailing slash) before
  deploying the frontend.

## 5. Authorization

Two layers, both required:

1. **Role permissions** — `IsStudent`, `IsInstitutionStaff`, `IsAdmin`,
   `IsSuperAdmin`, `IsStaffOrReadOnly` answer "may this kind of user do this
   kind of thing".
2. **Object ownership** — `IsEventOwner` and `IsInstitutionOwner` answer "does
   this user own this record". A staff account holding the general "may edit
   events" permission still cannot touch another institution's event.

Related hardening:

- `PATCH /api/users/me/` refuses to change `institution_id` for non-students,
  because staff ownership is derived from that field. Only an admin can move a
  staff account between institutions.
- Registration cannot self-assign an elevated role; a `role` field in the
  payload is ignored.
- Granting or removing `admin`/`super_admin` requires `super_admin`, and admins
  cannot suspend other administrators or themselves.
- Unverified events are invisible to students and anonymous visitors, so
  "save"/"register" on a draft returns 404 rather than leaking its existence.

## 6. Supabase Storage

- Only the backend holds `SUPABASE_SERVICE_ROLE_KEY`. It is never returned by an
  endpoint and never rendered into frontend code. Treat any exposure as a full
  database compromise and rotate immediately.
- Uploads are validated for content type (`image/jpeg`, `image/png`,
  `image/webp` by default) and size (5 MB default) before any network call.
- Object paths are generated server-side from a UUID, so a client cannot choose
  a path, traverse directories, or overwrite another user's object.
- Replacing an image deletes the object it supersedes; deleting an event deletes
  its cover after the database transaction commits.
- PostgreSQL stores URLs only; no binary media in the database, and nothing on
  Render's ephemeral disk.

## 7. Secrets

- Everything sensitive comes from the environment via `python-decouple`.
  `backend/.env` is gitignored; `backend/.env.example` documents the variables
  with placeholder values.
- `SECRET_KEY` must be a fresh, production-only value. Rotating it invalidates
  every issued JWT, since it is the signing key.
- `DEBUG=False` in production. With `DEBUG=False` the settings module also turns
  on SSL redirect, HSTS, and content-type nosniff.
- The Supabase connection uses SSL (`DB_SSL_REQUIRE=True` whenever `DEBUG` is
  off).

## 8. Error handling

All errors funnel through one envelope
(`{"detail", "code", "errors"}`) so no stack trace, SQL fragment or internal
path reaches a client. Login failures do not reveal whether an email exists —
unknown emails and wrong passwords both return "Invalid email or password."
Suspended accounts are told so deliberately, because that is actionable.

## 9. Pre-deployment checklist

- [ ] `DEBUG=False`
- [ ] Fresh `SECRET_KEY`, set only in the Render dashboard
- [ ] `ALLOWED_HOSTS` contains the Render host
- [ ] `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` contain the Netlify origin
- [ ] `JWT_COOKIE_SECURE=True`, `JWT_COOKIE_SAMESITE=None`
- [ ] `JWT_COOKIE_CSRF_ENFORCED=True`
- [ ] `DB_SSL_REQUIRE=True`
- [ ] `SUPABASE_SERVICE_ROLE_KEY` set on the backend only
- [ ] Storage buckets created with backend-controlled writes
- [ ] `python manage.py migrate` succeeded against Supabase
- [ ] A real super admin account exists and demo accounts are removed
