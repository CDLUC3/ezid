#!/usr/bin/env bash

cnt=$1

cp 77913_r7.bdb ~/.minders/77913/r7/nog.bdb && ./nog 77913/r7.mint "$cnt" > out.spings.nog
./bdb-util.py dump 77913 r7 > out.nog

cp 77913_r7.bdb ~/.minders/77913/r7/nog.bdb && python2.7 ./nog_minter.py 77913 r7 -c "$cnt" > out.spings.ez
./bdb-util.py dump 77913 r7 > out.ez

meld out.spings.nog out.spings.ez
#meld out.nog out.ez
