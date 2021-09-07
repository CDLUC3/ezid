#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#
file='./queue_table_dump.sql'

# Local access to production database by ssh tunnel
# mysql --compress --password --host 127.0.0.1 --port ${local_port} --user ezidro --database ezid

user='dahl'
pw=''
host='r2'
db='ezid'

table_arr=(
  'ezidapp_binderqueue'
  'ezidapp_crossrefqueue'
  'ezidapp_datacitequeue'
  'ezidapp_downloadqueue'
  'ezidapp_updatequeue'
)

dump() {
  printf 'Dumping queue tables to file: %s\n' "$file"

  cat /dev/null >"$file"

  for table in "${table_arr[@]}"; do
    printf 'Dumping queue table: %s\n' "$table"
    mysqldump >> "$file" "$db" "$table" --user="$user" --password="$pw" --host="$host" --no-tablespaces
  done
}

load() {
  printf 'Loading queue tables from file: %s\n' "$file"
  mysql < "$file" "$db" --user="$user" --password="$pw" --host="$host"
}

# dump
# load
