class Router (object):
  def db_for_read (self, model, **hints):
    if model._meta.db_table.startswith("ezidapp_search"):
      return "search"
    else:
      return None
  db_for_write = db_for_read
  def allow_migrate (self, db, app_label, model_name=None, **hints):
    return not ((db == "search") ^ model_name.startswith("search"))
