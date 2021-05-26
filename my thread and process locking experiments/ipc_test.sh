#!/usr/bin/env bash

# Test IPC

#
## set -x
#
#processes=10
#threads_per_proc=10 # not implemented
#loops_per_thread=1000
#
#rm -rf /tmp/procsc
#
#for (( i=0; i < processes; i++ )); do
#  printf 'Starting process %d\n' "$i"
#  ( ./ipc_client.py 'shared-name' --tag "proc-${i}" --loop "$loops_per_thread" --debug; ) &
#done
#
#read -p 'Hit Enter to stop the test'
#
## set +x
#
#kill "$(ps -s $$ -o pid=)"


# set -x

processes=10
threads_per_proc=1
loops_per_thread=100

printf 'Leftover procs:\n%s\n' "$(pgrep -af 'test')"

printf 'processes: %s\n' "$processes"
printf 'threads_per_proc: %s\n' "$threads_per_proc"
printf 'loops_per_thread: %s\n' "$loops_per_thread"

./ipc_test.py reset
./ipc_test.py state

for (( i=0; i < processes; i++ )); do
  ( ./ipc_test.py 'run_test' --tag "proc-${i}" --threads "$threads_per_proc" --loops "$loops_per_thread") &
done

wait

#read -p 'Hit Enter to stop the test'

printf 'Actual: %s\n' "$(./ipc_test.py state)"
printf 'Expected (processes * threads * loops_per_thread): %s\n' "$(( processes * threads_per_proc * loops_per_thread ))"



# set +x

#kill "$(ps -s $$ -o pid=)"
