#!/usr/bin/env bash

cat pre.sql <(pv prod-snapshot.sql.xz | unxz) post.sql | mysql -u ezidrw ezid
