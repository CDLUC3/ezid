use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# Add JSON metadata columns
# Time on stg-py3 host and DB with provisioned IO: 20 min
alter table `ezidapp_searchidentifier`
add column `metadata` json null check (json_valid(`metadata`));

# Time on stg-py3 host and DB with provisioned IO: 12 min
alter table `ezidapp_identifier`
add column `metadata` json null check (json_valid(`metadata`));