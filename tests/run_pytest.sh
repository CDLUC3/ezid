#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#

open_stack() {
  path="$1"

  file_rx='File +"(.*)", +line +([0-9]+), +in +(.*)'
  ez_rx='/dev/ezid-py3/'
  start_rx='^Traceback'
  stop_rx='^[^ ]'

  capture=0

  IFS=$'\n'
  for line in $(cat "$path"); do
    #printf 'capture=%s\n' "$capture"
    #printf 'line=%s\n' "$line"
    #printf 'func=%s\n' "$func"
    [[ "$line" =~ $start_rx ]] && {
      capture=1
      continue
    }
    [[ $capture == 0 ]] && {
      continue
    }
    [[ "$line" =~ $stop_rx ]] && [[ $capture == 1 ]] && {
      printf -- '---> %s\n' "$line"
      return
    }
    [[ "$line" =~ $ez_rx ]] && [[ "$line" =~ $file_rx ]] && {
      file="${BASH_REMATCH[1]}"
      lineno="${BASH_REMATCH[2]}"
      func="${BASH_REMATCH[3]}"
      printf 'Opening: %s:%s %s(\n' "$file" "$lineno" "$func"
      pycharm --line "$lineno" "$file" > /dev/null 2>&1
    }
  done
}

#  --capture=no
PYTEST_ARGS=(
  -vvv
  --failed-first
  --exitfirst
  --reuse-db
  --color=yes
  --log-cli-level=DEBUG
)

# Clear both the screen and scrollback buffer.
clear
echo -ne "\e[3J"

# We us 'meld' to check and resolve changes in tests results. When running under pytest,
# 'meld' is often left hanging, so we close any open instances. This sends SIGTERM, which
# allows the program to exit gracefully.
pkill -e 'meld'

pytest "${PYTEST_ARGS[@]}" "$@" | tee pytest.out

open_stack pytest.out
