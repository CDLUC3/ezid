#!/bin/bash
#
# emulates "hg identify -inb -R path"
#

# @executable

target_path='.'
if [ ! -z "${1}" ]; then
  target_path="${1}"
fi
pushd "${target_path}" > /dev/null
echo "$(git describe --abbrev=12 --always) $(git status --porcelain | wc -l | xargs) $(git branch --show-current)"
popd > /dev/null
