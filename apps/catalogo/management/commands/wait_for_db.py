"""Comando: espera a que PostgreSQL esté disponible antes de migrar."""

import time

import psycopg
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import OperationalError

TIMEOUT_SEGUNDOS = 60
INTERVALO_SEGUNDOS = 1


class Command(BaseCommand):
    help = "Espera a que la base de datos responda antes de continuar."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=TIMEOUT_SEGUNDOS,
            help="Máximo de segundos a esperar (por defecto 60).",
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]
        inicio = time.monotonic()
        intento = 0

        while True:
            intento += 1
            try:
                connections["default"].cursor()
            except (OperationalError, psycopg.Error) as error:
                elapsed = time.monotonic() - inicio
                if elapsed >= timeout:
                    self.stderr.write(
                        self.style.ERROR(
                            f"La base de datos no respondió en {timeout}s: {error}"
                        )
                    )
                    raise SystemExit(1) from error

                detalle = (
                    f"base={settings.DATABASES['default'].get('NAME')!r} "
                    f"host={settings.DATABASES['default'].get('HOST')!r}"
                )
                self.stdout.write(
                    f"   ... {detalle} no responde todavía (intento {intento}, "
                    f"{elapsed:.0f}s/{timeout}s)"
                )
                time.sleep(INTERVALO_SEGUNDOS)
            else:
                self.stdout.write(
                    self.style.SUCCESS("-> Base de datos disponible.")
                )
                return