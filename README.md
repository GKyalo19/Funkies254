## Funkies254

<a href="https://www.funkies254.com/" style="font-family: 'Courier New', monospace; font-size: 18px; margin-left: 20px;" target="_blank" rel="noopener noreferrer">Funkies254</a> is a platform for Kenyan high school and college students to discover student
events — academic competitions, sports tournaments, and social events — happening in (and
eventually beyond) Kenya. Students set their interests once, and the home feed curates
events for them.

<img width="2942" height="1724" alt="image" src="https://github.com/user-attachments/assets/f74100a1-756c-4534-800d-d1a83668cecb" />

## Tech stack

- **Backend**: Python, Django, Django REST Framework, SimpleJWT (httpOnly cookie auth)
- **Database & media storage**: PostgreSQL + Storage on Supabase 
- **Frontend**: Vanilla HTML, CSS, and JavaScript (ES modules, no build step)
- **Hosting**: Render (backend), Vercel (frontend)
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
