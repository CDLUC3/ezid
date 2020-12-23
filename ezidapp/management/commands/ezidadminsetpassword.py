import os.path

import django.contrib.auth.models
import django.core.management
import django.db.transaction

# The following must precede any EZID module imports:
exec(compile(open(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "tools",
        "offline.py",
    ), "rb"
).read(), os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "tools",
        "offline.py",
    ), 'exec'))

import config
import ezidapp.models


class Command(django.core.management.BaseCommand):
    help = "Set the EZID administrator password"

    def handle(self, *args, **options):
        u = config.get("auth.admin_username")
        p = config.get("auth.admin_password")
        with django.db.transaction.atomic():
            if not django.contrib.auth.models.User.objects.filter(username=u).exists():
                django.contrib.auth.models.User.objects.create_superuser(
                    username=u, password=None, email=""
                )
            o = ezidapp.models.getUserByUsername(u)
            o.setPassword(p)
            o.save()
