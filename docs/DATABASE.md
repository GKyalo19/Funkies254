# Funkies254 Database Reference

Django migrations are the authoritative schema history. Supabase PostgreSQL is
the target database; never create production tables by hand in Supabase and try
to reconstruct them in Django afterwards.

---

## 1. Entity relationship overview

```
User
 ├── institution_affiliation   (free-text school/org from signup)
 ├── institution_id ───────> Institution (nullable; staff/event scoping)
 ├── role
 └── 1:1 ──────────────────> UserPreference

Institution
 └── 1:M ──────────────────> Event

Event
 ├── M:M ──────────────────> Category   (through EventCategory)
 ├── school_level_id ──────> SchoolLevel (nullable)
 ├── created_by ───────────> User
 └── 1:M ──────────────────> EventRegistration

User ──1:M── SavedEvent ──M:1── Event
User ──1:M── EventRegistration ──M:1── Event

UserPreference ──M:M── Category  (through UserPreferenceCategory)
UserPreference ──FK──> SchoolLevel

AdminActivityLog ──FK──> User
```

Every table uses a UUID primary key, every timestamp is timezone-aware, and
media columns hold Supabase Storage URLs rather than binary data.

---

## 2. Tables

### `users` — `apps.users.models.User`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `email` | varchar(254) | No | Unique; normalised to lowercase |
| `name` | varchar(150) | No | Display name |
| `password` | varchar | No | Django hash from `AbstractBaseUser` |
| `avatar_url` | text | Yes | Supabase Storage URL |
| `role` | varchar(32) | No | `student`, `institution_staff`, `admin`, `super_admin` |
| `institution_affiliation` | varchar(200) | Yes | Free-text school/org the user typed; not a foreign key |
| `institution_id` | UUID FK → `institutions` | Yes | Staff/event scoping only; `ON DELETE SET NULL` |
| `is_active` | boolean | No | Suspension state |
| `is_staff` | boolean | No | Django admin access |
| `email_verified` | boolean | No | Default `false` for self-registered accounts |
| `email_verification_code_hash` | varchar(64) | No | SHA-256 of the current 6-digit code; blank once verified |
| `email_verification_sent_at` | timestamptz | Yes | Last time a code was emailed |
| `email_verification_attempts` | smallint | No | Failed verify attempts for the current code |
| `is_superuser` | boolean | No | Django full permissions |
| `last_login` | timestamptz | Yes | From `AbstractBaseUser` |
| `created_at` / `updated_at` | timestamptz | No | `auto_now_add` / `auto_now` |

There is deliberately no plaintext password column.

### `institutions` — `apps.organizers.models.Institution`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `name` | varchar(200) | No | |
| `email` | varchar(254) | Yes | Contact email |
| `phone` | varchar(32) | Yes | |
| `slug` | varchar(220) | No | Unique; generated from name |
| `logo_url` | text | Yes | Supabase Storage URL |
| `location` | text | Yes | Human-readable |
| `website` | varchar(200) | Yes | |
| `verified` | boolean | No | Default `false` |
| `created_by` | UUID FK → `users` | Yes | `ON DELETE SET NULL` |
| `created_at` / `updated_at` | timestamptz | No | |

### `school_levels` — `apps.events.models.SchoolLevel`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `name` | varchar(100) | No | Primary, Junior Secondary, Senior Secondary, College |
| `slug` | varchar(120) | No | Unique |

Kept as rows, not hard-coded event fields, so the taxonomy can evolve.

### `categories` — `apps.events.models.Category`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `name` | varchar(100) | No | Sports, Math, English, … |
| `slug` | varchar(120) | No | Unique |

### `events` — `apps.events.models.Event`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `title` | varchar(250) | No | |
| `slug` | varchar(280) | No | Unique; powers `GET /api/events/{slug}/` |
| `description` | text | No | |
| `institution_id` | UUID FK → `institutions` | Yes | `ON DELETE SET NULL` |
| `start_time` | timestamptz | No | |
| `end_time` | timestamptz | No | Must be after `start_time` |
| `venue` | varchar(250) | Yes | Null for virtual events |
| `location` | text | Yes | |
| `latitude` | numeric(9,6) | Yes | ±90 when present |
| `longitude` | numeric(9,6) | Yes | ±180 when present |
| `school_level_id` | UUID FK → `school_levels` | Yes | `ON DELETE SET NULL` |
| `cover_image_url` | text | Yes | Supabase Storage URL |
| `registration_link` | varchar(500) | Yes | External registration URL |
| `is_verified` | boolean | No | Admin verification state |
| `verified_by` | UUID FK → `users` | Yes | `ON DELETE SET NULL` |
| `verified_at` | timestamptz | Yes | |
| `is_virtual` | boolean | No | |
| `created_by` | UUID FK → `users` | No | `ON DELETE PROTECT` — history is never orphaned |
| `created_at` / `updated_at` | timestamptz | No | |

`slug` is not in the handwritten field list; it exists because the API contract
specifies slug-based event detail URLs. Coordinates stay provider-neutral —
geocoding is application logic, not a database concern.

### `event_categories` — `apps.events.models.EventCategory`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `event_id` | UUID FK → `events` | No | `ON DELETE CASCADE`, indexed |
| `category_id` | UUID FK → `categories` | No | `ON DELETE CASCADE`, indexed |

Explicit `through` model for the `Event ↔ Category` many-to-many.

### `saved_events` — `apps.events.models.SavedEvent`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `user_id` | UUID FK → `users` | No | `ON DELETE CASCADE`, indexed |
| `event_id` | UUID FK → `events` | No | `ON DELETE CASCADE`, indexed |
| `saved_at` | timestamptz | No | `auto_now_add` |

### `event_registrations` — `apps.registrations.models.EventRegistration`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `user_id` | UUID FK → `users` | No | `ON DELETE CASCADE`, indexed |
| `event_id` | UUID FK → `events` | No | `ON DELETE CASCADE`, indexed |
| `registered_at` | timestamptz | No | `auto_now_add` |
| `status` | varchar(16) | No | `registered`, `attended`, `cancelled`; indexed |

One row per `(user, event)`. Cancelling sets the status rather than deleting, so
re-registering reactivates the existing row and history is preserved.

### `user_preferences` — `apps.preferences.models.UserPreference`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `user_id` | UUID FK → `users` | No | Unique (one-to-one), `ON DELETE CASCADE` |
| `school_level_id` | UUID FK → `school_levels` | Yes | `ON DELETE SET NULL` |
| `email_notifications` | boolean | No | Default `true` |
| `push_notifications` | boolean | No | Default `false` |

### `user_preference_categories` — `apps.preferences.models.UserPreferenceCategory`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `user_preference_id` | UUID FK → `user_preferences` | No | `ON DELETE CASCADE`, indexed |
| `category_id` | UUID FK → `categories` | No | `ON DELETE CASCADE`, indexed |

### `admin_activity_log` — `apps.common.models.AdminActivityLog`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | UUID | No | Primary key |
| `user_id` | UUID FK → `users` | Yes | Actor; `ON DELETE SET NULL` so the trail survives account deletion |
| `action` | varchar(64) | No | From `apps.common.enums.AuditAction` |
| `table_name` | varchar(64) | No | Affected table |
| `record_id` | varchar(64) | Yes | Affected record; a string so deleted UUIDs remain readable |
| `created_at` | timestamptz | No | |

---

## 3. Constraints

| Constraint | Where |
|---|---|
| `users.email` unique | `User.email` |
| `institutions.slug` unique | `Institution.slug` |
| `categories.slug` unique | `Category.slug` |
| `school_levels.slug` unique | `SchoolLevel.slug` |
| `events.slug` unique | `Event.slug` |
| `unique_event_category (event_id, category_id)` | `EventCategory` |
| `unique_saved_event (user_id, event_id)` | `SavedEvent` |
| `unique_event_registration (user_id, event_id)` | `EventRegistration` |
| `user_preferences.user_id` unique | one-to-one field |
| `unique_user_preference_category (user_preference_id, category_id)` | `UserPreferenceCategory` |
| `event_end_time_after_start_time` CHECK | `Event` |
| `event_latitude_in_range` CHECK | `Event` (null or ±90) |
| `event_longitude_in_range` CHECK | `Event` (null or ±180) |

---

## 4. Indexes

| Table | Indexed columns |
|---|---|
| `users` | `email`, `institution_id`, `institution_affiliation`, `role` |
| `institutions` | `slug`, `verified` |
| `events` | `start_time`, `end_time`, `is_verified`, `institution_id`, `school_level_id` |
| `event_categories` | `event_id`, `category_id` |
| `saved_events` | `user_id`, `event_id` |
| `event_registrations` | `user_id`, `event_id`, `status` |
| `user_preference_categories` | `user_preference_id`, `category_id` |
| `admin_activity_log` | `user_id`, `table_name`, `record_id`, `created_at` |

Unique constraints and foreign keys add their own indexes on top of these.

---

## 5. Migration workflow

```bash
cd backend
source venv/bin/activate

python manage.py makemigrations          # after any model change
python manage.py sqlmigrate events 0001  # inspect the generated SQL
python manage.py migrate                 # apply locally
python manage.py seed_demo_data          # idempotent reference + demo data
```

Against Supabase, set `DATABASE_URL` and run the same `migrate`. Migration
order is forced by dependencies: `users` → `organizers` → `events` →
`registrations`/`preferences` → `common` (audit). Because `User` and
`Institution` reference each other, Django splits each into `0001_initial` plus
a `0002_initial` that adds the second foreign key.

### Definition of done

- [x] Every model has a migration, committed to git.
- [x] Every foreign key declares deliberate `on_delete` behaviour.
- [x] Every uniqueness requirement is a database constraint, not just serializer
      validation.
- [x] Required indexes exist.
- [x] `seed_demo_data` can run repeatedly without duplicating reference data.
- [x] Production Supabase is updated with `migrate`, never by hand.
- [x] No secret is hard-coded; everything comes from the environment.
