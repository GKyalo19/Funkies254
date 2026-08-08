from django.apps import AppConfig


class OrganizersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.organizers"
    label = "organizers"
    verbose_name = "Event Organizers"
