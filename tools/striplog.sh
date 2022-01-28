#! /usr/bin/env bash

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

# Strips dated (i.e., already rolled over) EZID transaction log files,
# retaining just BEGIN records for those transactions that
# successfully created, updated, or deleted a non-test identifier.
# Appends the resulting records to the master historical transaction
# log, and deletes the dated transaction logs.  The latter steps are
# performed only after a sanity check is performed and user
# confirmation.

shopt -s nullglob

FILTERLOG=`dirname $0`/filterlog
LOGDIR=`dirname $0`/../../logs
HISTDIR=$LOGDIR/historical
HISTLOG=$HISTDIR/master_transaction_log.gz

files=(${LOGDIR}/transaction_log.*)
if [ ${#files[@]} -eq 0 ]; then
  echo striplog: no transaction logs to process
  exit
fi

$FILTERLOG -CSD -s -R ${files[@]} | gzip > $HISTDIR/new.gz
gunzip -c $HISTLOG $HISTDIR/new.gz | gzip > $HISTDIR/combined.gz

mrc=`gunzip -c $HISTLOG | wc -l`
nrc=`gunzip -c $HISTDIR/new.gz | wc -l`
crc=`gunzip -c $HISTDIR/combined.gz | wc -l`
if [ $((mrc+nrc)) -ne $crc ]; then
  echo striplog: record count sanity check failed
  exit 1
fi

echo -n "Replace master log and delete dated transaction logs? [y/n] "
read yesno
if [ "$yesno" == "y" ]; then
  mv $HISTDIR/combined.gz $HISTLOG
  rm ${files[@]} $HISTDIR/new.gz
fi
