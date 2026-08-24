# Funkies254

Funkies254 is a platform for Kenyan high school and college students to discover student
events — academic competitions, sports tournaments, and social events — happening in (and
eventually beyond) Kenya. Students set their interests once, and the home feed curates
events for them.

```
Funkies254 Dev/
├── backend/     Django + Django REST Framework API
├── frontend/    Vanilla HTML/CSS/JS client
└── docs/        Architecture, setup, API reference, and deployment guides
```

## Quick start

```bash
# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo_data
python manage.py createsuperuser
python manage.py runserver 8000

# Frontend (in a second terminal)
cd frontend
python3 -m http.server 5500
```

Then open `http://127.0.0.1:5500/index.html`. Full instructions (including Supabase
setup): see [`docs/SETUP.md`](docs/SETUP.md).

To exercise the API on its own, import
[`docs/Funkies254.postman_collection.json`](docs/Funkies254.postman_collection.json) into
Postman and run **Auth → Login (student)** first — authentication is cookie-based and
Postman replays the cookies automatically.

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/FILE_GUIDE.md`](docs/FILE_GUIDE.md) | File-by-file map of the whole repo — what each file does and where to go to change something |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Why each technology was chosen, how the frontend/backend/database talk to each other |
| [`docs/SETUP.md`](docs/SETUP.md) | Step-by-step local dev setup, including Supabase configuration and Postman testing |
| [`docs/API.md`](docs/API.md) | Every REST endpoint, request/response shapes, and `curl` examples |
| [`docs/DATABASE.md`](docs/DATABASE.md) | ERD, table-by-table schema, constraints, indexes, migration workflow |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Cookies, CORS/CSRF, roles and ownership, secrets, storage access |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Deploying for free to Render (backend) + Netlify (frontend) |

## Tech stack

- **Backend**: Python, Django, Django REST Framework, SimpleJWT (httpOnly cookie auth)
- **Database & media storage**: PostgreSQL + Storage on Supabase (free tier)
- **Frontend**: Vanilla HTML, CSS, and JavaScript (ES modules, no build step)
- **Hosting**: Render (backend), Netlify (frontend) — both free tiers
- **Testing**: pytest + pytest-django

## Status

The backend implements the full specification with 148 passing tests: cookie-JWT
authentication, four roles with object-level ownership checks, institutions with admin
verification, curated events with categories and school levels, saved events,
transactional registrations, per-user preferences, a rule-based recommendation feed,
audit logging of every privileged action, and Supabase Storage for media.

Deliberately not built, because the schema for them is not confirmed: event capacity,
featured events, organizer follows, notification history, and password reset. See
`docs/API.md` for what exists today.
