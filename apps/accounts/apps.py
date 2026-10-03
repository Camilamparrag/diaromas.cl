from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Cuentas"

    def ready(self):
        # Importa las señales que crean el Profile de cada usuario
        from . import signals  # noqa: F401