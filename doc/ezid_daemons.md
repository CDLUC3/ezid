---
title: EZID Daemons
subtitle: Daemons operating in support of the EZID application.
---

The EZID application utilizes several background processes to perform actions asynchronous with user inputs.

The background processes include:

`proc-binder`

: TODO

`proc-crossref`

: TODO

`proc-datacite`

: TODO

`proc-download`

: TODO

`proc-link-checker`

: TODO

`proc-link-checker-update`

: TODO

`proc-newsfeed`

: Examines the news feed URL and pushes new items to the `NewsFeed` model (ezidapp_)

`proc-search-indexer`

: Updates the searchIdentifier model with changes to the identifier table. Watches the `SearchIndexerQueue` 
  queue table, responding to create, update, and delete signals.

`proc-stats`

: Computes statistics periodically. Previously computed statistics are completely replaced. Runs once a day.

