#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import django.conf


class Router(object):
    def db_for_read(self, model, **_hints):
        # noinspection PyProtectedMember
        t = model._meta.db_table
        if t.startswith("ezidapp_search") or t == "ezidapp_linkchecker":
            return "search"
        else:
            return "default"

    db_for_write = db_for_read

    def allow_migrate(self, db, app_label, model_name=None, **_hints):
        return True
