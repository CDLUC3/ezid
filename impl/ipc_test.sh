#!/usr/bin/env bash

# Test IPC

# set -x

processes=10
threads_per_proc=10 # not implemented
loops_per_thread=1000

rm -rf /tmp/procsc

for (( i=0; i < "$processes"; i++ )); do
  printf 'Starting process %d\n' "$i"
  ( ./ipc_client.py 'shared-name' --tag "proc-${i}" --loop "$loops_per_thread" --debug; ) &
done

read -p 'Hit Enter to stop the test'

# set +x

kill "$(ps -s $$ -o pid=)"
