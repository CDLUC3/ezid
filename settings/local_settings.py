from settings.settings_generated import *

for db_name in ('default', 'search'):
    DATABASES[db_name].update(
        {
            "HOST": "r2",
            "NAME": "ezid",
            # "NAME": "ezid_test_db",
            "USER": "ezid_test_user",
            "PASSWORD": "",
        }
    )

MINTERS_PATH = PROJECT_ROOT / 'db' / 'minters'
