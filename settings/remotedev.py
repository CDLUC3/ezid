import settings.common

DEPLOYMENT_LEVEL = "remotedev"

STANDALONE = True

# True: Use MYSQL
# False: Use SQLite
STORE_MYSQL = True
SEARCH_MYSQL = True

# If both the store and search databases are on MySQL, they share a single database.
SEARCH_STORE_SAME_DATABASE = STORE_MYSQL and SEARCH_MYSQL

ALLOWED_HOSTS = [
    '*',
    'ezid-stg.cdlib.org',
    'uc3-ezidx2-dev.cdlib.org',
    'uc3-ezidui01x2-stg.cdlib.org',
    'localhost',
    '127.0.0.1',
    '172.31.57.125',
]

settings.common.injectSecrets(DEPLOYMENT_LEVEL)
