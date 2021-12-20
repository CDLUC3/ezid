use ezid;

set unique_checks = 0;
set foreign_key_checks = 0;

# Search tables are generally subsets of the corresponding store tables. The datacenter tables are an exception, so we
# must copy a few entries over search to store.
insert into ezidapp_storedatacenter(symbol, name)
select a.symbol, a.symbol from ezidapp_searchdatacenter a
where a.symbol not in (select symbol from ezidapp_storedatacenter)
;