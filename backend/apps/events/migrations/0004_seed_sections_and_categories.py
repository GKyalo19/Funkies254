from django.db import migrations

from apps.events.taxonomy import seed_taxonomy


def seed(apps, schema_editor):
    seed_taxonomy(apps, schema_editor)
    Event = apps.get_model("events", "Event")
    Event.objects.filter(is_virtual=True).update(format="online")


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0003_eventinteraction_searchquery_section_and_more"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
