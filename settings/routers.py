import django.conf

class Router (object):
  def db_for_read (self, model, **hints):
    t = model._meta.db_table
    if t.startswith("ezidapp_search") or t == "ezidapp_linkchecker":
      return "search"
    else:
      return "default"
  db_for_write = db_for_read
  def allow_migrate (self, db, app_label, model_name=None, **hints):
    if django.conf.settings.SEARCH_STORE_SAME_DATABASE:
      return True
    else:
      return not ((db == "search") ^\
        (app_label == "ezidapp" and (model_name.startswith("search") or\
        model_name == "linkchecker")))
