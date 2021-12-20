#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#

[[ -n $DB_HOST && -n $DB_PORT && -n $DB_USER && -n $DB_PW && -n $DB_NAME ]] || {
  printf 'Must set environment variables: DB_HOST, DB_PORT, DB_USER, DB_PW, DB_NAME\n'
  exit 1
}

cnf_path='/tmp/db.cnf'

printf 'Running migration...\n'

start_sec=$SECONDS
prev_sec=$start_sec

set -e

mysql_args=(
  --defaults-extra-file="$cnf_path"
  --default-character-set=utf8mb4
  --unbuffered
  --quick
  --verbose
  "$DB_NAME"
)

#  "--port=$DB_PORT"
#  "--host=$DB_HOST"
#  "--user=$DB_USER"
#  "--password=$DB_PW"

cat > "$cnf_path" << EOF
[client]
host = "$DB_HOST"
port = "$DB_PORT"
user = "$DB_USER"
password = "$DB_PW"
EOF

step() {
  printf '\n\n#### %s\n' "$1"
  f="./sql/schema-migration.$1.sql"
  grep "^#" "$f"
  mysql  "${mysql_args[@]}" < "$f"
  printf 'Step elapsed: %ss\n' "$((SECONDS - prev_sec))"
  prev_sec=$SECONDS
}

step 1
step 2
step 3

step 4
./db-migrate-blobs-to-metadata.py search
./db-migrate-blobs-to-metadata.py store

step 5
./db-update-fk.py

step 6
step 7

# To create a new DB fixture, stop the migration here.

step 8

printf 'EZID can now be started for local testing\n'

step 9
printf 'Completed. Total elapsed: %ss\n' "$((SECONDS - start_sec))"
