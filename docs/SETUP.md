# Funkies254 — Local Setup Guide

This guide gets the full stack (backend + frontend) running on your machine. It assumes
no prior Django/backend experience.

## Prerequisites

- **Python 3.11–3.13** (Python 3.14 is too new — some dependencies don't yet ship
  pre-built wheels for it. Check with `python3 --version`.)
- A modern browser (Chrome, Firefox, Safari, Edge).
- No Node.js/npm required — the frontend has no build step.

---

## 1. Backend setup

```bash
cd backend

# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate            # Windows: venv\Scripts\activate

# 2. Install dependencies (requirements-dev.txt includes pytest etc.)
pip install -r requirements-dev.txt

# 3. Create your local environment file
cp .env.example .env
# Open .env and at minimum leave DATABASE_URL blank for now —
# the app automatically falls back to a local sqlite database file.

# 4. Apply database migrations
python manage.py migrate

# 5. (Optional, recommended) Load demo events/organizers/categories
python manage.py seed_demo_data

# 6. Create an admin account so you can log into /admin/ and curate events
python manage.py createsuperuser

# 7. Run the dev server
python manage.py runserver 8000
```

The API is now live at `http://127.0.0.1:8000/api/`. Visit
`http://127.0.0.1:8000/admin/` and log in with the superuser you just created to browse
and curate events/organizers/categories through Django's built-in admin.

### Running backend tests

```bash
cd backend
source venv/bin/activate
pytest                 # or: python manage.py test
```

All tests use a temporary sqlite database — they never touch your real data or Supabase.

---

## 2. Frontend setup

The frontend is plain HTML/CSS/JS — there's nothing to install. You do need to serve it
over `http://` (not open the `.html` files directly via `file://`), because ES modules
(`<script type="module">`) and `fetch()` cookies don't work reliably over `file://`.

**Option A — Python's built-in server (simplest, no install needed):**

```bash
cd frontend
python3 -m http.server 5500
```

Then open `http://127.0.0.1:5500/index.html`.

**Option B — VS Code "Live Server" extension:**

Right-click `frontend/index.html` → "Open with Live Server". By default it also serves
on port 5500, which matches the CORS configuration below.

> **Important:** whichever method you use, serve from **port 5500** (or update
> `CORS_ALLOWED_ORIGINS` in `backend/.env` to match whatever port you actually use).

---

## 3. Connecting frontend ↔ backend locally

With both servers running:

- Frontend: `http://127.0.0.1:5500`
- Backend: `http://127.0.0.1:8000`

`frontend/js/utils/config.js` automatically points at `http://127.0.0.1:8000/api` when
the page is opened from `localhost`/`127.0.0.1`, so no changes are needed for local dev.
`backend/.env`'s `CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500`
already allows the frontend origin to send credentialed requests (the httpOnly auth
cookies).

Open `http://127.0.0.1:5500/index.html` — you should see the seeded demo events. Try
registering an account, setting preferences, and registering for an event to confirm the
whole stack talks to itself correctly.

---

## 4. Setting up Supabase (Postgres + Storage) — needed before deploying

Local dev works fine with sqlite and no file uploads configured, but you'll need Supabase
before deploying so:
1. Go to [supabase.com](https://supabase.com) → **New project** (free tier).
2. **Database**: Project Settings → Database → copy the **Connection string (URI)** →
   paste it into `backend/.env` as `DATABASE_URL`.
3. **Storage**: Storage → **New bucket** → name it `funkies254-media` (or update
   `SUPABASE_STORAGE_BUCKET` to match) → make it **public** (so uploaded event covers/
   avatars are viewable without extra signed-URL logic).
4. **API keys**: Project Settings → API → copy the **Project URL** into
   `SUPABASE_URL`, and the **service_role key** (not the public `anon` key — the service
   role key is needed to upload files) into `SUPABASE_SERVICE_ROLE_KEY`.
5. Re-run `python manage.py migrate` once `DATABASE_URL` points at Supabase, so your
   schema is created there too.

⚠️ The service role key bypasses Row Level Security — never expose it to the frontend or
commit it to git. It only ever lives in `backend/.env` (local) or Render's environment
variables (deployed).

---

## 5. Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `pip install` fails building `Pillow` from source | Python version too new for the pinned Pillow release to have a pre-built wheel | Use Python 3.11–3.13, or update the `Pillow` version in `requirements.txt` |
| Frontend shows "Could not reach the server" toasts | Backend isn't running, or wrong port | Confirm `python manage.py runserver 8000` is running and reachable at `http://127.0.0.1:8000/api/events/` |
| Login "works" but `/api/users/me/` returns 401 right after | Frontend served over a different port than `5500`/CORS mismatch | Update `CORS_ALLOWED_ORIGINS` in `backend/.env` to match your actual frontend origin, restart the backend |
| Avatar/event image upload fails with 502 | Supabase Storage env vars not set | Follow section 4 above; local dev without Supabase configured will always fail file uploads (everything else still works) |

Next: see `docs/API.md` for the full endpoint reference, and `docs/DEPLOYMENT.md` for
hosting for free on Netlify + Render.
