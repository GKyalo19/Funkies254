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

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/FILE_GUIDE.md`](docs/FILE_GUIDE.md) | File-by-file map of the whole repo — what each file does and where to go to change something |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Why each technology was chosen, how the frontend/backend/database talk to each other, folder-by-folder breakdown |
| [`docs/SETUP.md`](docs/SETUP.md) | Step-by-step local dev setup, including Supabase configuration |
| [`docs/API.md`](docs/API.md) | Every REST endpoint, request/response shapes, and `curl` examples |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Deploying for free to Render (backend) + Netlify (frontend) |

## Tech stack

- **Backend**: Python, Django, Django REST Framework, SimpleJWT (httpOnly cookie auth)
- **Database & media storage**: PostgreSQL + Storage on Supabase (free tier)
- **Frontend**: Vanilla HTML, CSS, and JavaScript (ES modules, no build step)
- **Hosting**: Render (backend), Netlify (frontend) — both free tiers
- **Testing**: pytest + pytest-django

## Status

Core flows are implemented and tested end-to-end: registration/login/logout/password
reset, browsing + filtering events, event detail with follow/register, preferences that
drive a curated home feed, profile management with avatar uploads, and a staff-only event
creation tool. See the todo list in `docs/ARCHITECTURE.md` §8 for the planned growth path
(mobile app, real ML-based recommendations, organizer self-service).
