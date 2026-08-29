from django.db import migrations, models


def copy_linked_institution_name(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.filter(
        institution_id__isnull=False, institution_affiliation__isnull=True
    ).select_related("institution"):
        if user.institution_id and user.institution:
            user.institution_affiliation = user.institution.name
            user.save(update_fields=["institution_affiliation"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_email_verification"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="institution_affiliation",
            field=models.CharField(
                blank=True,
                help_text="Free-text school, university or organization the user typed at signup.",
                max_length=200,
                null=True,
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["institution_affiliation"], name="users_affiliation_idx"
            ),
        ),
        migrations.RunPython(copy_linked_institution_name, migrations.RunPython.noop),
    ]
