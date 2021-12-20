use ezid;

set unique_checks = 0;
set foreign_key_checks = 0;

# Decode blobs to JSON and write them to the new metadata columns.

# searchidentifier: ~20 min
# ./db-migrate-blobs-to-metadata.py search

# storeidentifier: ~10 min
# ./db-migrate-blobs-to-metadata.py store