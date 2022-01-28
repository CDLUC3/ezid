#! /usr/bin/env bash

# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD

# Emulates "hg identify -inb -R path" after move from hg to git

target_path='.'
if [ ! -z "${1}" ]; then
  target_path="${1}"
fi
pushd "${target_path}" > /dev/null
echo "$(git describe --abbrev=12 --always) $(git status --porcelain | wc -l | xargs) $(git branch --show-current)"
popd > /dev/null
