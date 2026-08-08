# Funkies254 — Deployment Guide (all free tiers)

This deploys the backend to **Render**, the frontend to **Netlify**, and the database +
media storage to **Supabase** — no credit card required for any of them at this scale.

Do this **after** local setup works (see `docs/SETUP.md`) and you've pushed the repo to
GitHub (both Render and Netlify deploy from a git repo).

---

## 1. Supabase (do this first — the backend needs it)

1. Create a free project at [supabase.com](https://supabase.com).
2. **Database** → Project Settings → Database → copy the **Connection string (URI)**.
   You'll paste this into Render as `DATABASE_URL` in step 2.
3. **Storage** → New bucket → name `funkies254-media` → toggle **Public bucket** on.
4. **API** → Project Settings → API → copy the **Project URL** (`SUPABASE_URL`) and the
   **service_role** secret key (`SUPABASE_SERVICE_ROLE_KEY`).

---

## 2. Backend → Render

### Option A: Blueprint (recommended — uses `backend/render.yaml`)

1. Push your repo to GitHub.
2. On [render.com](https://render.com): **New +** → **Blueprint** → select your repo.
   Render reads `backend/render.yaml` and creates the web service automatically.
3. After it's created, go to the service's **Environment** tab and add the variables
   that aren't in `render.yaml` (because they're secrets/deployment-specific):

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | The Supabase connection string from step 1 |
   | `SUPABASE_URL` | From step 1 |
   | `SUPABASE_SERVICE_ROLE_KEY` | From step 1 |
   | `SUPABASE_STORAGE_BUCKET` | `funkies254-media` |
   | `CORS_ALLOWED_ORIGINS` | `https://<your-netlify-site>.netlify.app` (set after step 3) |
   | `FRONTEND_BASE_URL` | Same as above — used to build password reset links |
   | `EMAIL_BACKEND` | Keep `django.core.mail.backends.console.EmailBackend` until you configure a real SMTP provider; reset emails will just show up in Render's logs meanwhile |

4. **Manual Deploy** → trigger a deploy. Render will `pip install`, run
   `collectstatic`, then start `gunicorn`.
5. Once live, visit `https://<your-service>.onrender.com/api/events/categories/` to
   confirm the API responds. Then run migrations + seed data via Render's **Shell** tab:
   ```bash
   python manage.py migrate
   python manage.py seed_demo_data
   python manage.py createsuperuser
   ```

### Option B: Manual web service (no Blueprint)

1. **New +** → **Web Service** → connect your repo.
2. **Root Directory**: `backend`
3. **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. **Start Command**: `gunicorn config.wsgi:application`
5. Add the same environment variables as Option A, **plus** `SECRET_KEY` (generate one,
   e.g. `python -c "import secrets; print(secrets.token_urlsafe(50))"`), `DEBUG=False`,
   `ALLOWED_HOSTS=.onrender.com`, `JWT_COOKIE_SECURE=True`.

> **Free tier note:** Render's free web services spin down after inactivity and take
> ~30–60s to "wake up" on the next request. That's expected — not a bug — while testing.

---

## 3. Frontend → Netlify

1. On [netlify.com](https://netlify.com): **Add new site** → **Import an existing
   project** → connect your repo.
2. **Base directory**: `frontend`
3. **Build command**: leave blank (no build step).
4. **Publish directory**: `frontend` (or `.` if you set base directory to `frontend`).
5. Deploy. Netlify gives you a URL like `https://funkies254.netlify.app`.
6. **Update the backend's real URL in the frontend**: edit
   `frontend/js/utils/config.js` and set `RENDER_API_URL` to your actual Render service
   URL (e.g. `https://funkies254-api.onrender.com/api`), commit, and push — Netlify
   redeploys automatically on every push to your main branch.
7. Go back to Render and set `CORS_ALLOWED_ORIGINS` / `FRONTEND_BASE_URL` to your real
   Netlify URL (from step 5), then redeploy the backend so the new CORS origin takes
   effect.

---

## 4. Post-deploy checklist

- [ ] `https://<netlify-site>/index.html` loads and shows seeded events.
- [ ] Registering a new account works end-to-end (check Render's logs if it fails —
      almost always a `CORS_ALLOWED_ORIGINS` or `DATABASE_URL` mismatch).
- [ ] `JWT_COOKIE_SECURE=True` is set on Render (cross-site cookies **require** `Secure`
      + `SameSite=None`, which `config/settings.py` sets automatically when this is
      `True` — see `JWT_COOKIE_SAMESITE`).
- [ ] Uploading an avatar/event cover image works (confirms Supabase Storage creds and
      bucket "Public" toggle are correct).
- [ ] `/admin/` is reachable and you can log in with the superuser you created.

## 5. Custom domain (optional, later)

Both Netlify and Render support free custom domains + automatic HTTPS. Point your DNS
at Netlify for the frontend (e.g. `funkies254.com`) and a subdomain at Render for the API
(e.g. `api.funkies254.com`), then update `CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS`, and
`frontend/js/utils/config.js` to match.
