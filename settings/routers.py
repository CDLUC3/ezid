class Router (object):
  def db_for_read (self, model, **hints):
    if model._meta.db_table.startswith("ezidapp_search"):
      return "search"
    else:
      return "default"
  db_for_write = db_for_read
  def allow_migrate (self, db, app_label, model_name=None, **hints):
    return not ((db == "search") ^\
      (app_label == "ezidapp" and model_name.startswith("search")))
