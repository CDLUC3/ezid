import os.path

from common import *

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True

# True: Use MYSQL
# False: Use SQLite
STORE_MYSQL = True
SEARCH_MYSQL = True

# If both the store and search databases are on MySQL, they share a single database.
SEARCH_STORE_SAME_DATABASE = STORE_MYSQL and SEARCH_MYSQL

ALLOWED_HOSTS = ["uc3-ezidx2-dev.cdlib.org", "localhost", "127.0.0.1"]

injectSecrets(DEPLOYMENT_LEVEL)
