#!/usr/bin/env bash

#
# Copyright©2021, Regents of the University of California
# http://creativecommons.org/licenses/BSD
#

# Mint 1,000,000 spings with the 77913/r7 minter / shoulder using Perl N2T Nog.
# Store with line numbers.
cp test_docs/77913_r7.bdb ~/.minders/77913/r7/nog.bdb
time ./nog 77913/r7.mint 1000000 | nl > nog_perl_1m.csv
