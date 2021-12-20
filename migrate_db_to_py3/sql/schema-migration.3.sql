use ezid;

set unique_checks = 0;
set foreign_key_checks = 0;

# Add JSON metadata columns
# Time on stg-py3 host and DB with provisioned IO, searchidentifier: 20 min
alter table `ezidapp_searchidentifier`
add column `metadata` json null check (json_valid(`metadata`));

# Time on stg-py3 host and DB with provisioned IO, storeidentifier: 12 min
alter table `ezidapp_storeidentifier`
add column `metadata` json null check (json_valid(`metadata`));