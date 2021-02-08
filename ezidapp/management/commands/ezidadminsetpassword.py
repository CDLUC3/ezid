import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.store_user
import impl.config


class Command(django.core.management.BaseCommand):
    help = "Set the EZID administrator password"

    def handle(self, *args, **options):
        u = impl.config.get("auth.admin_username")
        p = impl.config.get("auth.admin_password")
        with django.db.transaction.atomic():
            if not django.contrib.auth.models.User.objects.filter(username=u).exists():
                django.contrib.auth.models.User.objects.create_superuser(
                    username=u, password=None, email=""
                )
            o = ezidapp.models.store_user.getUserByUsername(u)
            o.setPassword(p)
            o.save()
