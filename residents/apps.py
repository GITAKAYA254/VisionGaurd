from django.apps import AppConfig


class ResidentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "residents"

    def ready(self):
        import residents.signals  # noqa: F401
