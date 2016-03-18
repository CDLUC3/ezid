from common import *

DEPLOYMENT_LEVEL = "localdev"

STANDALONE = True
SSL = False
RELOAD_TEMPLATES = True

DATABASES["default"] = {
  "ENGINE": "django.db.backends.sqlite3",
  "NAME": os.path.join(SITE_ROOT, "db", "store.sqlite3"),
  "OPTIONS": { "timeout": 60 }
}
SECRET_PATHS.remove(("DATABASES", "default", "HOST"))
SECRET_PATHS.remove(("DATABASES", "default", "PASSWORD"))

ALLOWED_HOSTS = ["localhost"]
LOCALIZATIONS = { "default": ("cdl", ["andy.mardesich@ucop.edu"]) }
LOCALIZATIONS["localhost:8001"] = ("purdue", ["gjanee@ucop.edu"])
LOCALIZATIONS["localhost:8002"] = ("jisc-edina", ["gjanee@ucop.edu"])

injectSecrets(DEPLOYMENT_LEVEL)

# Andy's MySQL driver won't allow utf8mb4 for some reason.
DATABASES["search"]["OPTIONS"]["charset"] = "utf8"
