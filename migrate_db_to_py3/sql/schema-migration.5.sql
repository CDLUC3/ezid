use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# Decode blobs to JSON and write them to the new metadata columns.

-- Run: db-migrate-blobs-to-metadata.py