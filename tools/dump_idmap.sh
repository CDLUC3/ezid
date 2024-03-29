#! /usr/bin/env bash

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

# Extracts all agent identifiers from an EZID dump file
# (gzip-compressed or not) and prints a mapping of agent identifiers
# to local names.

tooldir=`dirname $0`

if [ $# -eq 0 ]; then
  cat=cat
  infile=
elif [ $# -eq 1 ]; then
  if [[ $1 =~ .*\.gz$ ]]; then
    cat="gunzip -c"
  else
    cat=cat
  fi
  infile=$1
else
  echo "usage: $0 [dumpfile]" >&2
  exit 1
fi

# The use of fgrep below is purely for performance.

$cat $infile |\
  fgrep _ezid_role |\
  $tooldir/ezid_select.py _fields contains _ezid_role |\
  $tooldir/project.py -d -s \| _id ezid.group.groupname ezid.user.username\
    _ezid_role |\
  awk -F \| '{ print $1, ($4 == "user"? $3 : $2), "(" $4 ")" }' |\
  sort -k 2,2 -k 3,3r
