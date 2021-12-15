use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# Translate from search to store FKs in ezidapp_searchidentifier
# Time on stg-py3 host and DB: 17 min
# Time on stg-py3 host and dev DB: 24 min (probably starting with full level of burst tokens)
# Run db-update-fk.py