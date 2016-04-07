import django.contrib.auth.models
import django.core.management.base
import os.path

# The following must precede any EZID module imports:
execfile(os.path.join(os.path.dirname(os.path.dirname(
  os.path.dirname(os.path.dirname(__file__)))), "tools", "offline.py"))

import config

class Command (django.core.management.base.BaseCommand):
  help = "Set the EZID administrator password"
  def handle (self, *args, **options):
    u = config.get("ldap.admin_username")
    p = config.get("ldap.admin_password")
    try:
      o = django.contrib.auth.models.User.objects.get(username=u)
      o.set_password(p)
      o.save()
    except django.contrib.auth.models.User.DoesNotExist:
      django.contrib.auth.models.User.objects.create_superuser(
        username=u, password=p, email="")
