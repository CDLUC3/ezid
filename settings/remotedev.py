from common import *

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True

# True: Use MYSQL
# False: Use SQLite
STORE_MYSQL = True
SEARCH_MYSQL = True

# If both the store and search databases are on MySQL, they share a single database.
SEARCH_STORE_SAME_DATABASE = STORE_MYSQL and SEARCH_MYSQL

ALLOWED_HOSTS = [
    u'ezid-stg.cdlib.org',
    u'uc3-ezidx2-dev.cdlib.org',
    u'uc3-ezidui01x2-stg.cdlib.org',
    u'localhost',
    u'127.0.0.1',
    u'172.31.57.125',
]

injectSecrets(DEPLOYMENT_LEVEL)
