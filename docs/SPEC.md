# Funkies254 — Pre-launch change spec

This is the product contract for the public launch. Read it with `docs/DATABASE.md`
and `docs/API.md` before changing models, endpoints, or pages.

Funkies254 is a view-only discovery site. Visitors find events here and register
on the organiser's own site. The site has three sections: College Events, High
School Events, and College Application Resources (a Coming soon placeholder).

## Events (EVT)

- Cards and the event page send people to `registration_link`. They do not
  create an on-site registration.
- `POST /api/registrations/` returns `410` with `code: registration_external`
  and the organiser link when the event can be resolved.
- `GET /api/events/` returns upcoming events only, unless `search` is set or
  `upcoming` is passed explicitly. Search lists upcoming matches first, then
  past matches, and writes a `search_queries` row.
- A published event needs an `https://` registration link. The column stays
  nullable so drafts and historical rows can exist. Verifying an event without
  that link is refused.
- `format` is `in_person`, `online`, or `hybrid`. `is_virtual` remains as a
  stored boolean synced from `format == online`.
- Views and click-outs are stored on `event_interactions`. A view from the same
  user or IP counts once per hour.

## Categories (CAT)

- Sections: `college-events`, `high-school-events`, `college-app-resources`.
- Categories belong to a section. College Application Resources has no live
  events; the homepage shows an under-construction graphic.
- Public school levels are Junior Secondary, Senior Secondary, and College.
  Primary stays in the database and is hidden from `GET /api/school-levels/`.

## Accounts (ACC)

- After email verification, a student without preferences is sent to
  `/pages/profile.html?tab=preferences&onboarding=1`.
- Preferences cover sections, categories, format, weekdays/weekends, country,
  city, optional coordinates (rounded to two decimals), max distance
  (10, 25, 50, 100, or empty), include-other-countries, free-only, and email
  notifications.
- Signed-in users can change their password and delete their own account.
- The service account `agent@funkies254.com` has role `agent` and cannot sign in.

## Cards, ranking, navigation (CARD, RANK, NAV)

- Any signed-in user can bookmark an event. Unsaving shows an Undo toast.
- Visitors are ranked by popularity, then soonest start. Signed-in users with
  preferences are ranked by preference match, then distance, then popularity.
- Popularity over 30 days is `3 * saves + 2 * click-outs + 1 * views + 5 * external_mentions`.
- The header is the logo, search, and login or avatar. It picks up a blue bar
  after the page scrolls.

## Agent (AGENT)

- A daily job proposes new or updated events. Proposals wait in the admin
  review queue. Approving or rejecting writes `AdminActivityLog`.
- Agent-created events are never auto-verified.
- `GET /api/admin/health-report/latest/` summarises the latest run.
- `POST /api/newsletter/` stores a footer subscriber.

## Pages (HOME, ABOUT, FOOT)

- Home: hero, a popular or recommended strip, the three section blocks, and
  browse-all.
- About names the product and thanks Andrew Chelimo.
- The footer has three columns plus a newsletter form.
- `frontend/pages/registrations.html` is removed. Historical registration rows
  remain readable through the API.
