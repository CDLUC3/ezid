#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#

naan=77913
shoulder=r7
mint_count=6000

target="${naan}_${shoulder}_${mint_count}"
state_nog="${target}.nog.state.txt"
state_ezid="${target}.ezid.state.txt"
spings_nog="${target}.nog.spings.txt"
spings_ezid="${target}.ezid.spings.txt"

function resetdb() {
    cp "${naan}_$shoulder.bdb" "$HOME/.minders/${naan}/${shoulder}/nog.bdb"
}

resetdb && ./nog "${naan}/${shoulder}.mint" "${mint_count}" > "${spings_nog}"
./nog_minter.py "${naan}" "${shoulder}" --dump > "${state_nog}"

resetdb && python2.7 ./nog_minter.py "${naan}" "${shoulder}" -c "${mint_count}" > "${spings_ezid}"
./nog_minter.py "${naan}" "${shoulder}" --dump > "${state_ezid}"

md5sum "${state_nog}" "${state_ezid}"
meld "${state_nog}" "${state_ezid}"
