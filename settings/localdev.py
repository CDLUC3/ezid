from common import *

DEPLOYMENT_LEVEL = "localdev"

STANDALONE = True
RELOAD_TEMPLATES = True

DATABASES["default"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "HOST": "databases.store_host",
    "NAME": os.path.join(PROJECT_ROOT, "db", "store.sqlite3"),
    "OPTIONS": {"timeout": 60},
    "PASSWORD": "databases.store_password",
}

DATABASES["search"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "HOST": "databases.search_host",
    "NAME": os.path.join(PROJECT_ROOT, "db", "search.sqlite3"),
    "OPTIONS": {"timeout": 60},
    "PASSWORD": "databases.search_password",
    "fulltextSearchSupported": True,
}

SECRET_PATHS.remove(("DATABASES", "default", "HOST"))
SECRET_PATHS.remove(("DATABASES", "default", "PASSWORD"))
SEARCH_STORE_SAME_DATABASE = False

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
LOCALIZATIONS = {"default": ("cdl", ["somebody@ucop.edu"])}

injectSecrets(DEPLOYMENT_LEVEL)

# Andy's MySQL driver won't allow utf8mb4 for some reason.
# If enabled, this line causes initial setup of the search database to fail.
# DATABASES["search"]["OPTIONS"]["charset"] = "utf8"
