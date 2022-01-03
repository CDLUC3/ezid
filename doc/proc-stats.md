---
title: EZID proc-stats
---

Computes counts of identifiers for unique combinations of `(Month of creation, 
owner id, group id, identifier type, identifier has metadata)`.

It does this for all users.

The results appear in the `Statistics` model, which corresponds to the `ezidapp_statistics` table.

Notes:

This process loops through all identifiers, and does so with many queries that pull 1000 entries at a time
from the list of identifiers, sorted by identifier.

If user_id x identifier never changes, then these stats really only need to be computed on recently created 
identifiers (over the preceding month). 
