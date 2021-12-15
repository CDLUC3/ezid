use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# Translate from search to store FKs in ezidapp_searchidentifier
# Time on stg-py3 host and DB: 17 min
# Time on stg-py3 host and dev DB: 24 min (probably starting with full level of burst tokens)
# Run db-update-fk.py

# Drop the 'stub' tables that exist only to support ezidapp_searchidentifier when located in another DB.
# These tables contain copies of some of the columns in the corresponding store* tables. The only search*
# table that remains afterwards is ezidapp_searchidentifier.
drop table ezidapp_searchdatacenter;
drop table ezidapp_searchgroup;
drop table ezidapp_searchprofile;
drop table ezidapp_searchrealm;
drop table ezidapp_searchuser;

# Since we no longer have "search" tables, we can now remove the "store" prefixes on the remaining tables.
rename table ezidapp_storedatacenter to ezidapp_datacenter;
rename table ezidapp_storegroup to ezidapp_group;
rename table ezidapp_storegroup_shoulders to ezidapp_group_shoulders;
rename table ezidapp_storeidentifier to ezidapp_identifier;
rename table ezidapp_storeprofile to ezidapp_profile;
rename table ezidapp_storerealm to ezidapp_realm;
rename table ezidapp_storeuser to ezidapp_user;
rename table ezidapp_storeuser_proxies to ezidapp_user_proxies;
rename table ezidapp_storeuser_shoulders to ezidapp_user_shoulders;

# alter table ezidapp_searchuser
# drop foreign key ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id,
# drop foreign key ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id
# ;
#
# alter table ezidapp_searchuser
# drop key ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id
# ;