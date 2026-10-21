# Funkies254 — Deployment Guide (all free tiers)

This deploys the backend to **Render**, the frontend to **Vercel**, and the database +
media storage to **Supabase** — no credit card required for any of them at this scale.

Do this **after** local setup works (see `docs/SETUP.md`) and you've pushed the repo to
GitHub (both Render and Vercel deploy from a git repo).

---

## 1. Supabase (do this first — the backend needs it)

1. Create a free project at [supabase.com](https://supabase.com).
2. **Database** → Project Settings → Database → copy the **Connection string (URI)**.
   You'll paste this into Render as `DATABASE_URL` in step 2. Prefer the connection
   pooler URI on the free tier; it survives more concurrent connections.
3. **Storage** → New bucket, twice:
   - `event-covers` → **Public bucket** on (event covers are public content).
   - `avatars` → public or private, depending on your privacy decision. Either way,
     uploads are performed by the backend only.
4. **API** → Project Settings → API → copy the **Project URL** (`SUPABASE_URL`) and the
   **service_role** secret key (`SUPABASE_SERVICE_ROLE_KEY`).

The service-role key bypasses Row Level Security. It belongs in Render's environment
variables and nowhere else — never in the frontend, never in git.

---

## 2. Backend → Render

### Option A: Blueprint (recommended — uses `backend/render.yaml`)

1. Push your repo to GitHub.
2. On [render.com](https://render.com): **New +** → **Blueprint** → select your repo.
   Render reads `backend/render.yaml` and creates the web service automatically.
   `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, and the cookie/CSRF flags are declared
   there.
3. After it's created, go to the service's **Environment** tab and add the variables that
   aren't in `render.yaml` (because they're secrets or deployment-specific):

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | The Supabase connection string from step 1 |
   | `DB_SSL_REQUIRE` | `True` |
   | `SUPABASE_URL` | From step 1 |
   | `SUPABASE_SERVICE_ROLE_KEY` | From step 1 |
   | `SUPABASE_BUCKET_EVENT_COVERS` | `event-covers` |
   | `SUPABASE_BUCKET_AVATARS` | `avatars` |
   | `CORS_ALLOWED_ORIGINS` | `https://www.funkies254.com,https://funkies254.com,https://funkies254.vercel.app` |
   | `CSRF_TRUSTED_ORIGINS` | Same as above |
   | `FRONTEND_BASE_URL` | `https://www.funkies254.com` |

4. **Manual Deploy** → trigger a deploy. Render will `pip install`, run `collectstatic`,
   then start `gunicorn`. The `Procfile` release phase runs `migrate` on every deploy, so
   the Supabase schema stays in step with your migrations.
5. Once live, check `https://<your-service>.onrender.com/api/health/`. Then seed the
   reference data and create a real administrator through Render's **Shell** tab:

   ```bash
   python manage.py migrate                        # no-op if the release phase ran it
   python manage.py seed_demo_data --reference-only # categories + school levels only
   python manage.py createsuperuser                 # your real super admin
   ```

   Use `--reference-only` in production: the full command also creates demo accounts with
   a published password.

### Option B: Manual web service (no Blueprint)

1. **New +** → **Web Service** → connect your repo.
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. **Start Command**: `gunicorn config.wsgi:application`
5. Add the same environment variables as Option A, **plus**:

   | Key | Value |
   |---|---|
   | `SECRET_KEY` | Generate one: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `.onrender.com` |
   | `JWT_COOKIE_SECURE` | `True` |
   | `JWT_COOKIE_SAMESITE` | `None` |
   | `JWT_COOKIE_CSRF_ENFORCED` | `True` |

> **Free tier note:** Render's free web services spin down after inactivity and take
> ~30–60s to "wake up" on the next request. That's expected — not a bug — while testing.

---

## 3. Frontend → Vercel

1. On [vercel.com](https://vercel.com): **Add New** → **Project** → import the repo.
2. **Root directory**: `frontend`
3. **Framework preset**: Other. Leave the build command blank.
4. `frontend/vercel.json` already sets security headers. There is no SPA rewrite;
   each page is a real HTML file.
5. Deploy. The project URL is `https://funkies254.vercel.app`. The GoDaddy domain
   `funkies254.com` (apex and `www`) points at that same project.
6. **Point the frontend at the real backend**: `frontend/js/utils/config.js` should
   use `https://funkies254-api.onrender.com/api`.
7. On Render, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` must list
   `https://www.funkies254.com`, `https://funkies254.com`, and
   `https://funkies254.vercel.app`. `FRONTEND_BASE_URL` is
   `https://www.funkies254.com` (scheme included). Redeploy the API after changing them.

### Why the cookie flags matter here

Vercel and Render are different sites, so the auth cookies are cross-site. Browsers only
send cross-site cookies when they are `SameSite=None; Secure`, and they reject
`SameSite=None` without `Secure`. If login appears to succeed but the next request is
401, this pairing is almost always the cause.

---

## 4. Post-deploy checklist

- [ ] `GET /api/health/` returns `{"status": "ok"}`.
- [ ] `GET /api/categories/` returns the seeded taxonomy (confirms the Supabase
      connection and that migrations ran).
- [ ] `https://www.funkies254.com/index.html` loads and shows events.
- [ ] Registering a new account works end-to-end. If it fails, check Render's logs —
      it is almost always a `CORS_ALLOWED_ORIGINS`, cookie-flag or `DATABASE_URL`
      mismatch.
- [ ] `JWT_COOKIE_SECURE=True` and `JWT_COOKIE_SAMESITE=None` are set on Render.
- [ ] `JWT_COOKIE_CSRF_ENFORCED=True` on Render, and the frontend echoes `X-CSRFToken`
      on writes.
- [ ] Uploading an avatar or event cover works (confirms the Supabase Storage
      credentials and bucket names).
- [ ] `/admin/` is reachable and your super admin can log in.
- [ ] `DEBUG=False`, and the demo accounts from `seed_demo_data` do not exist in
      production.

## 5. Custom domain (optional, later)

Vercel and Render both attach HTTPS to custom domains. GoDaddy DNS for
`funkies254.com` and `www.funkies254.com` points at the Vercel project. The API
stays on `funkies254-api.onrender.com`. Any new frontend origin has to be added
to `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` before login will work there.
