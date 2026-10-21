"""Launch sections and categories (CAT-1, CAT-3). Shared by migrations and seeding."""

SECTIONS = (
    {
        "name": "College Events",
        "slug": "college-events",
        "description": "Events for college and university students.",
        "sort_order": 1,
    },
    {
        "name": "High School Events",
        "slug": "high-school-events",
        "description": "Events for junior and senior secondary students.",
        "sort_order": 2,
    },
    {
        "name": "College Application Resources",
        "slug": "college-app-resources",
        "description": "Guides for applying to college. Coming soon.",
        "sort_order": 3,
    },
)

# Existing rows keep these slugs so event tags and preferences survive.
HIGH_SCHOOL_EXISTING = (
    ("Math", "math", "/assets/icons/cat-math.svg"),
    ("Sciences", "sciences", "/assets/icons/cat-sciences.svg"),
    ("Languages", "languages", "/assets/icons/cat-languages.svg"),
    ("Humanities", "humanities", "/assets/icons/cat-humanities.svg"),
    ("Sports", "sports", "/assets/icons/cat-sports.svg"),
    ("Chess", "chess", "/assets/icons/cat-chess.svg"),
    ("English", "english", None),
    ("Music", "music", None),
)

HIGH_SCHOOL_NEW = (
    ("Coding & Robotics", "coding-robotics", None),
    ("Debate & Public Speaking", "debate-public-speaking", None),
    ("Arts & Music", "arts-music", None),
    ("Leadership & Community Service", "leadership-community-service", None),
    ("Holiday Programmes", "holiday-programmes", None),
)

COLLEGE_CATEGORIES = (
    ("Engineering & Technology", "engineering-technology", None),
    ("Computer Science & AI", "computer-science-ai", None),
    ("Health & Medicine", "health-medicine", None),
    ("Law & Policy", "law-policy", None),
    ("Business & Entrepreneurship", "business-entrepreneurship", None),
    ("Natural Sciences", "natural-sciences", None),
    ("Humanities & Social Sciences", "humanities-social-sciences", None),
    ("Arts & Design", "arts-design", None),
    ("Internships & Careers", "internships-careers", None),
    ("Scholarships & Fellowships", "scholarships-fellowships", None),
)


def seed_taxonomy(apps, schema_editor=None):
    """Idempotent seed used by the data migration and manage.py seed_demo_data."""
    Section = apps.get_model("events", "Section")
    Category = apps.get_model("events", "Category")

    sections = {}
    for row in SECTIONS:
        section, _ = Section.objects.get_or_create(
            slug=row["slug"],
            defaults={
                "name": row["name"],
                "description": row["description"],
                "sort_order": row["sort_order"],
                "is_active": True,
            },
        )
        sections[row["slug"]] = section

    def upsert(section_slug, rows):
        section = sections[section_slug]
        for order, (name, slug, icon) in enumerate(rows, start=1):
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "section": section,
                    "icon_url": icon,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            if not created and category.section_id is None:
                category.section = section
                category.icon_url = category.icon_url or icon
                category.sort_order = category.sort_order or order
                category.save(update_fields=["section", "icon_url", "sort_order"])

    upsert("high-school-events", HIGH_SCHOOL_EXISTING + HIGH_SCHOOL_NEW)
    upsert("college-events", COLLEGE_CATEGORIES)
