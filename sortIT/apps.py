from django.apps import AppConfig


class SortITConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sortIT"

    def ready(self):
        from . import signals  # noqa: F401
