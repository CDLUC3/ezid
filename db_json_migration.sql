/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */






# Fresh start on migrations
# delete from django_migrations
#
#     Remove migrations from your migrations folder for the app
#
# rm -rf <app>/migrations/
#
#     Reset the migration for builtin apps(like admin)
#
# python manage.py migrate --fake
#
#     Create initial migration for each and every app
#
# python manage.py makemigrations <app>
#
#     The final step is to create fake initial migrations
#
# python manage.py migrate --fake-initial

#  Apply all migrations: admin, auth, contenttypes, ezidapp, sessions

#  admin
#  auth
#  contenttypes
#  sessions
#  ezidapp

#  ./manage.py migrate contenttypes
#  ./manage.py migrate admin
#  ./manage.py migrate auth
#  ./manage.py migrate sessions
#  ./manage.py migrate ezidapp


# Drop all of Django's internal tables
set foreign_key_checks = 0;
drop table if exists auth_group cascade;
drop table if exists auth_group_permissions cascade;
drop table if exists auth_permission cascade;
drop table if exists auth_user cascade;
drop table if exists auth_user_groups cascade;
drop table if exists auth_user_user_permissions cascade;
drop table if exists django_admin_log cascade;
drop table if exists django_content_type cascade;
drop table if exists django_migrations cascade;
drop table if exists django_session cascade;
set foreign_key_checks = 1;

# show create table ezid_test_db.django_content_type;
# create table `django_content_type`
# (
#     `id`        int          not null auto_increment,
#     `app_label` varchar(100) not null,
#     `model`     varchar(100) not null,
#     primary key (`id`),
#     unique key `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`, `model`)
# ) engine = InnoDB
#   auto_increment = 32
#   default charset = latin1
# ;

delete from test3.django_migrations dm where dm.app = 'ezidapp';

```bash
rm -rf ezidapp/migrations/*
./manage.py migrate contenttypes
./manage.py migrate
./manage.py migrate --fake
./manage.py makemigrations ezidapp
./manage.py migrate --fake-initial
```


show index from ezidapp_refidentifier;
alter table ezidapp_refidentifier
    drop index identifier;
alter table ezidapp_refidentifier
    add index identifier using btree (identifier);

# Rename columns to remove all 'store' prefixes
# MySQL 5
alter table ezidapp_user_shoulders change column storeuser_id user_id int;
alter table ezidapp_group_shoulders change column storegroup_id group_id int;
alter table ezidapp_user_proxies change column from_storeuser_id from_user_id int;
alter table ezidapp_user_proxies change column to_storeuser_id to_user_id int;
# MariaDB
alter table ezidapp_user_shoulders rename column storeuser_id to user_id;
alter table ezidapp_group_shoulders rename column storegroup_id to group_id;
alter table ezidapp_user_proxies rename column from_storeuser_id to from_user_id;
alter table ezidapp_user_proxies rename column to_storeuser_id to to_user_id;
;

# Rename the tables to remove all 'store' prefixes.
rename table ezidapp_storedatacenter to ezidapp_datacenter;
rename table ezidapp_storegroup to ezidapp_group;
rename table ezidapp_storegroup_shoulders to ezidapp_group_shoulders;
rename table ezidapp_storeidentifier to ezidapp_identifier;
rename table ezidapp_storeprofile to ezidapp_profile;
rename table ezidapp_storerealm to ezidapp_realm;
rename table ezidapp_storeuser to ezidapp_user;
rename table ezidapp_storeuser_proxies to ezidapp_user_proxies;
rename table ezidapp_storeuser_shoulders to ezidapp_user_shoulders;

select concat_ws(' ', 'rename table', table_name, 'to', replace(table_name, '_store', '_'), ';')
from information_schema.tables
where table_schema = 'ezid'
  and table_name like 'ezidapp_store%'
order by table_name
;

# Drop the 'stub' tables that exist only to support ezidapp_searchidentifier when located in another DB.
# These tables contain copies of some of the columns in the corresponding store* tables. The only search*
# table that remains afterwards is ezidapp_searchidentifier.
drop table ezidapp_searchdatacenter;
drop table ezidapp_searchgroup;
drop table ezidapp_searchprofile;
drop table ezidapp_searchrealm;
drop table ezidapp_searchuser;

# MySQL (same as MariaDB, except using 'foreign key' instead of 'constraint')

alter table ezidapp_searchgroup
    drop foreign key ezidapp_sear_realm_id_58cd72178e312e42_fk_ezidapp_searchrealm_id;
alter table ezidapp_searchidentifier
    drop foreign key ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id;
alter table ezidapp_searchidentifier
    drop foreign key ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id;
alter table ezidapp_searchidentifier
    drop foreign key ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id;
alter table ezidapp_searchidentifier
    drop foreign key ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id;
alter table ezidapp_searchuser
    drop foreign key ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id;
alter table ezidapp_shoulder
    drop foreign key ezid_datacenter_id_4fb7570a75b0c69_fk_ezidapp_storedatacenter_id;
alter table ezidapp_shoulder
    drop foreign key ezidapp_shoulder_registration_agency__ba15f13e_fk_ezidapp_r;
alter table ezidapp_shoulder
    drop foreign key ezidapp_shoulder_shoulder_type_id_184bbced_fk_ezidapp_s;
alter table ezidapp_storegroup
    drop foreign key ezidapp_store_realm_id_3405b66a3ee93b42_fk_ezidapp_storerealm_id;
alter table ezidapp_storegroup_shoulders
    drop foreign key ezidapp__storegroup_id_59e419f89a47aef8_fk_ezidapp_storegroup_id;
alter table ezidapp_storegroup_shoulders
    drop foreign key ezidapp_stor_shoulder_id_592128c84020a89a_fk_ezidapp_shoulder_id;
alter table ezidapp_storeidentifier
    drop foreign key ezi_datacenter_id_3bc5951853d0443c_fk_ezidapp_storedatacenter_id;
alter table ezidapp_storeidentifier
    drop foreign key ezidapp__ownergroup_id_10bf8aa5ea27b4bd_fk_ezidapp_storegroup_id;
alter table ezidapp_storeidentifier
    drop foreign key ezidapp_s_profile_id_4105f1929b18ac77_fk_ezidapp_storeprofile_id;
alter table ezidapp_storeidentifier
    drop foreign key ezidapp_storei_owner_id_2a042b1b01e4a83b_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser
    drop foreign key ezidapp_store_group_id_7eff2039d02834ed_fk_ezidapp_storegroup_id;
alter table ezidapp_storeuser
    drop foreign key ezidapp_store_realm_id_5d5c037d7f3fac93_fk_ezidapp_storerealm_id;
alter table ezidapp_storeuser_proxies
    drop foreign key ezidapp_storeuser_pr_from_storeuser_id_4dc227f6_fk_ezidapp_s;
alter table ezidapp_storeuser_proxies
    drop foreign key ezidapp_storeuser_pr_to_storeuser_id_5588e255_fk_ezidapp_s;
alter table ezidapp_storeuser_shoulders
    drop foreign key ezidapp_st_storeuser_id_6730d06357e88738_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser_shoulders
    drop foreign key ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id;

select concat_ws(' ', 'alter table', table_name, 'drop foreign key', constraint_name, ';')
from information_schema.key_column_usage
where referenced_table_schema = 'ezid'
  and referenced_table_name like 'ezidapp_%';


# MariaDB

# Queries generated by query below, all search* tables
# ezidapp_searchuser,group_id,ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id,ezidapp_searchgroup,id
alter table ezidapp_searchuser
    drop constraint ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id;
# ezidapp_searchuser,realm_id,ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id,ezidapp_searchrealm,id
alter table ezidapp_searchuser
    drop constraint ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id;
# ezidapp_searchidentifier,datacenter_id,ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id,ezidapp_searchdatacenter,id
alter table ezidapp_searchidentifier
    drop constraint ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id;
# ezidapp_searchidentifier,profile_id,ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id,ezidapp_searchprofile,id
alter table ezidapp_searchidentifier
    drop constraint ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id;
# ezidapp_searchidentifier,ownergroup_id,ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id,ezidapp_searchgroup,id
alter table ezidapp_searchidentifier
    drop constraint ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id;
# ezidapp_searchidentifier,owner_id,ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id,ezidapp_searchuser,id
alter table ezidapp_searchidentifier
    drop constraint ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id;
# ezidapp_searchgroup,realm_id,ezidapp_sear_realm_id_58cd72178e312e42_fk_ezidapp_searchrealm_id,ezidapp_searchrealm,id
alter table ezidapp_searchgroup
    drop constraint ezidapp_sear_realm_id_58cd72178e312e42_fk_ezidapp_searchrealm_id;

# Queries generated by query below, all store* tables
# ezidapp_storeuser_shoulders,shoulder_id,ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id,ezidapp_shoulder,id
alter table ezidapp_storeuser_shoulders
    drop constraint ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id;
# ezidapp_storeuser_proxies,from_storeuser_id,ezida_from_storeuser_id_199e0c23a1cd56a7_fk_ezidapp_storeuser_id,ezidapp_storeuser,id
alter table ezidapp_storeuser_proxies
    drop constraint ezida_from_storeuser_id_199e0c23a1cd56a7_fk_ezidapp_storeuser_id;
# ezidapp_storeuser_proxies,to_storeuser_id,ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id,ezidapp_storeuser,id
alter table ezidapp_storeuser_proxies
    drop constraint ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id;
# ezidapp_storegroup,realm_id,ezidapp_store_realm_id_3405b66a3ee93b42_fk_ezidapp_storerealm_id,ezidapp_storerealm,id
alter table ezidapp_storegroup
    drop constraint ezidapp_store_realm_id_3405b66a3ee93b42_fk_ezidapp_storerealm_id;
# ezidapp_storegroup_shoulders,storegroup_id,ezidapp__storegroup_id_59e419f89a47aef8_fk_ezidapp_storegroup_id,ezidapp_storegroup,id
alter table ezidapp_storegroup_shoulders
    drop constraint ezidapp__storegroup_id_59e419f89a47aef8_fk_ezidapp_storegroup_id;
# ezidapp_storegroup_shoulders,shoulder_id,ezidapp_stor_shoulder_id_592128c84020a89a_fk_ezidapp_shoulder_id,ezidapp_shoulder,id
alter table ezidapp_storegroup_shoulders
    drop constraint ezidapp_stor_shoulder_id_592128c84020a89a_fk_ezidapp_shoulder_id;
# ezidapp_storeuser,group_id,ezidapp_store_group_id_7eff2039d02834ed_fk_ezidapp_storegroup_id,ezidapp_storegroup,id
alter table ezidapp_storeuser
    drop constraint ezidapp_store_group_id_7eff2039d02834ed_fk_ezidapp_storegroup_id;
# ezidapp_storeuser,realm_id,ezidapp_store_realm_id_5d5c037d7f3fac93_fk_ezidapp_storerealm_id,ezidapp_storerealm,id
alter table ezidapp_storeuser
    drop constraint ezidapp_store_realm_id_5d5c037d7f3fac93_fk_ezidapp_storerealm_id;
# ezidapp_storeidentifier,datacenter_id,ezi_datacenter_id_3bc5951853d0443c_fk_ezidapp_storedatacenter_id,ezidapp_storedatacenter,id
alter table ezidapp_storeidentifier
    drop constraint ezi_datacenter_id_3bc5951853d0443c_fk_ezidapp_storedatacenter_id;
# ezidapp_storeidentifier,ownergroup_id,ezidapp__ownergroup_id_10bf8aa5ea27b4bd_fk_ezidapp_storegroup_id,ezidapp_storegroup,id
alter table ezidapp_storeidentifier
    drop constraint ezidapp__ownergroup_id_10bf8aa5ea27b4bd_fk_ezidapp_storegroup_id;
# ezidapp_storeidentifier,profile_id,ezidapp_s_profile_id_4105f1929b18ac77_fk_ezidapp_storeprofile_id,ezidapp_storeprofile,id
alter table ezidapp_storeidentifier
    drop constraint ezidapp_s_profile_id_4105f1929b18ac77_fk_ezidapp_storeprofile_id;
# ezidapp_storeidentifier,owner_id,ezidapp_storei_owner_id_2a042b1b01e4a83b_fk_ezidapp_storeuser_id,ezidapp_storeuser,id
alter table ezidapp_storeidentifier
    drop constraint ezidapp_storei_owner_id_2a042b1b01e4a83b_fk_ezidapp_storeuser_id;
# ezidapp_storeuser_shoulders,storeuser_id,ezidapp_st_storeuser_id_6730d06357e88738_fk_ezidapp_storeuser_id,ezidapp_storeuser,id
alter table ezidapp_storeuser_shoulders
    drop constraint ezidapp_st_storeuser_id_6730d06357e88738_fk_ezidapp_storeuser_id;
# ezidapp_shoulder,datacenter_id,ezid_datacenter_id_4fb7570a75b0c69_fk_ezidapp_storedatacenter_id,ezidapp_storedatacenter,id
alter table ezidapp_shoulder
    drop constraint ezid_datacenter_id_4fb7570a75b0c69_fk_ezidapp_storedatacenter_id;

## test3
alter table ezidapp_shoulder
    drop constraint ezidapp_shoulder_datacenter_id_077f6b18_fk_ezidapp_s;
alter table ezidapp_shoulder
    drop constraint ezidapp_shoulder_registration_agency__ba15f13e_fk_ezidapp_r;
alter table ezidapp_shoulder
    drop constraint ezidapp_shoulder_shoulder_type_id_184bbced_fk_ezidapp_s;
alter table ezidapp_searchgroup
    drop constraint ezidapp_searchgroup_realm_id_2c9c3c52_fk_ezidapp_searchrealm_id;
alter table ezidapp_group
    drop constraint ezidapp_storegroup_realm_id_0c342308_fk_ezidapp_storerealm_id;
alter table ezidapp_group_shoulders
    drop constraint ezidapp_storegroup_s_storegroup_id_ba874e30_fk_ezidapp_s;
alter table ezidapp_group_shoulders
    drop constraint ezidapp_storegroup_s_shoulder_id_77a48100_fk_ezidapp_s;
alter table ezidapp_user
    drop constraint ezidapp_storeuser_group_id_44816d9d_fk_ezidapp_storegroup_id;
alter table ezidapp_user
    drop constraint ezidapp_storeuser_realm_id_90d87e43_fk_ezidapp_storerealm_id;
alter table ezidapp_user_shoulders
    drop constraint ezidapp_storeuser_sh_shoulder_id_bb6c79e0_fk_ezidapp_s;
alter table ezidapp_user_shoulders
    drop constraint ezidapp_storeuser_sh_storeuser_id_f6a0e6d4_fk_ezidapp_s;
alter table ezidapp_user_proxies
    drop constraint ezidapp_storeuser_pr_from_storeuser_id_4dc227f6_fk_ezidapp_s;
alter table ezidapp_user_proxies
    drop constraint ezidapp_storeuser_pr_to_storeuser_id_5588e255_fk_ezidapp_s;
alter table ezidapp_searchuser
    drop constraint ezidapp_searchuser_group_id_611f6dd8_fk_ezidapp_searchgroup_id;
alter table ezidapp_searchuser
    drop constraint ezidapp_searchuser_realm_id_c56160f4_fk_ezidapp_searchrealm_id;
alter table ezidapp_searchidentifier
    drop constraint ezidapp_searchidenti_datacenter_id_cf60d753_fk_ezidapp_s;
alter table ezidapp_searchidentifier
    drop constraint ezidapp_searchidenti_ownergroup_id_5148144b_fk_ezidapp_s;
alter table ezidapp_searchidentifier
    drop constraint ezidapp_searchidenti_profile_id_0e5a20cb_fk_ezidapp_s;
alter table ezidapp_searchidentifier
    drop constraint ezidapp_searchidenti_owner_id_f7eedd30_fk_ezidapp_s;

# Generate queries for dropping foreign key constraints on all ezidapp_ tables
select concat_ws(' ', 'alter table', table_name, 'drop constraint', constraint_name, ';'),
       table_name,
       column_name,
       constraint_name,
       referenced_table_name,
       referenced_column_name
from information_schema.key_column_usage
where referenced_table_schema = 'test3'
  and referenced_table_name like 'ezidapp_%';


select ( select count(*) from ezidapp_searchdatacenter ) as searchdatacenter,
       ( select count(*) from ezidapp_storedatacenter )  as storedatacenter,
       ( select count(*) from ezidapp_searchgroup )      as searchgroup,
       ( select count(*) from ezidapp_storegroup )       as storegroup,
       ( select count(*) from ezidapp_searchidentifier ) as searchidentifier,
       ( select count(*) from ezidapp_storeidentifier )  as storeidentifier,
       ( select count(*) from ezidapp_searchprofile )    as searchprofile,
       ( select count(*) from ezidapp_storeprofile )     as storeprofile,
       ( select count(*) from ezidapp_searchrealm )      as searchrealm,
       ( select count(*) from ezidapp_storerealm )       as storerealm,
       ( select count(*) from ezidapp_searchuser )       as searchuser,
       ( select count(*) from ezidapp_storeuser )        as storeuser
;


# searchdatacenter
# storedatacenter
# searchgroup
# storegroup
# searchidentifier
# storeidentifier
# searchprofile
# storeprofile
# searchrealm
# storerealm
# searchuser
# storeuser

select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchdatacenter';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storedatacenter';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchgroup';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storegroup';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchidentifier';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storeidentifier';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchprofile';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storeprofile';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchrealm';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storerealm';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_searchuser';
select column_name
from information_schema.columns
where table_schema = 'ezid'
  and table_name = 'ezidapp_storeuser';

##

alter table `ezidapp_searchidentifier`
    add column metadata json default null;
alter table `ezidapp_storeidentifier`
    add column metadata json default null;
update ezidapp_searchidentifier
set metadata = '{}';
update ezidapp_storeidentifier
set metadata = '{}';

kill 50;

show full processlist;

# Time of last update for any storeIdentifier (indicates when the DB was last used)
select from_unixtime(max(updateTime))
from ezidapp_storeidentifier es;

drop index `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_365b2611` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_keywords` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_resourceCreator` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_resourcePublisher` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_resourceTitle` on ezidapp_searchidentifier;
drop index `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx` on ezidapp_searchidentifier;

drop index `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx` on ezidapp_searchidentifier;

##

show create table ezidapp_searchidentifier;

create table `ezidapp_searchidentifier`
(
    `id`                        int(11)                                            not null auto_increment,
    `identifier`                varchar(255) character set ascii collate ascii_bin not null,
    `createTime`                int(11)                                            not null,
    `updateTime`                int(11)                                            not null,
    `status`                    varchar(1)                                         not null,
    `unavailableReason`         longtext character set utf8mb4                     not null,
    `exported`                  tinyint(1)                                         not null,
    `crossrefStatus`            varchar(1)                                         not null,
    `crossrefMessage`           longtext character set utf8mb4                     not null,
    `target`                    varchar(2000)                                      not null,
    `cm`                        longblob                                           not null,
    `agentRole`                 varchar(1)                                         not null,
    `isTest`                    tinyint(1)                                         not null,
    `owner_id`                  int(11)                                            not null,
    `ownergroup_id`             int(11)                                            not null,
    `datacenter_id`             int(11) default null,
    `profile_id`                int(11)                                            not null,
    `searchableTarget`          varchar(255)                                       not null,
    `resourceCreator`           longtext character set utf8mb4                     not null,
    `resourceTitle`             longtext character set utf8mb4                     not null,
    `resourcePublisher`         longtext character set utf8mb4                     not null,
    `resourcePublicationDate`   longtext character set utf8mb4                     not null,
    `searchablePublicationYear` int(11) default null,
    `resourceType`              longtext character set utf8mb4                     not null,
    `searchableResourceType`    varchar(2)                                         not null,
    `keywords`                  longtext character set utf8mb4                     not null,
    `resourceCreatorPrefix`     varchar(50) character set utf8mb4                  not null,
    `resourceTitlePrefix`       varchar(50) character set utf8mb4                  not null,
    `resourcePublisherPrefix`   varchar(50) character set utf8mb4                  not null,
    `hasMetadata`               tinyint(1)                                         not null,
    `publicSearchVisible`       tinyint(1)                                         not null,
    `oaiVisible`                tinyint(1)                                         not null,
    `hasIssues`                 tinyint(1)                                         not null,
    `linkIsBroken`              tinyint(1)                                         not null,
    primary key (`id`),
    unique key `identifier` (`identifier`),
    key `ezidapp_searchidentifier_5e7b1936` (`owner_id`),
    key `ezidapp_searchidentifier_365b2611` (`ownergroup_id`),
    key `ezidapp_searchidentifier_13bc2970` (`datacenter_id`),
    key `ezidapp_searchidentifier_83a0eb3f` (`profile_id`),
    key `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx` (`owner_id`, `identifier`),
    key `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx` (`ownergroup_id`, `identifier`),
    key `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx` (`owner_id`, `createTime`),
    key `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx` (`owner_id`, `updateTime`),
    key `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx` (`owner_id`, `status`),
    key `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx` (`owner_id`, `exported`),
    key `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx` (`owner_id`, `crossrefStatus`),
    key `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx` (`owner_id`, `profile_id`),
    key `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx` (`owner_id`, `isTest`),
    key `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx` (`owner_id`, `searchablePublicationYear`),
    key `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx` (`owner_id`, `searchableResourceType`),
    key `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx` (`owner_id`, `hasMetadata`),
    key `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx` (`owner_id`, `hasIssues`),
    key `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx` (`owner_id`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx` (`owner_id`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx` (`owner_id`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx` (`ownergroup_id`, `createTime`),
    key `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx` (`ownergroup_id`, `updateTime`),
    key `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx` (`ownergroup_id`, `status`),
    key `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx` (`ownergroup_id`, `exported`),
    key `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx` (`ownergroup_id`, `crossrefStatus`),
    key `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx` (`ownergroup_id`, `profile_id`),
    key `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx` (`ownergroup_id`, `isTest`),
    key `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx` (`ownergroup_id`, `searchablePublicationYear`),
    key `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx` (`ownergroup_id`, `searchableResourceType`),
    key `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx` (`ownergroup_id`, `hasMetadata`),
    key `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx` (`ownergroup_id`, `hasIssues`),
    key `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx` (`ownergroup_id`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx` (`ownergroup_id`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx` (`ownergroup_id`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx` (`publicSearchVisible`, `identifier`),
    key `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx` (`publicSearchVisible`, `createTime`),
    key `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx` (`publicSearchVisible`, `updateTime`),
    key `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx` (`publicSearchVisible`, `searchablePublicationYear`),
    key `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx` (`publicSearchVisible`, `searchableResourceType`),
    key `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx` (`publicSearchVisible`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx` (`publicSearchVisible`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx` (`publicSearchVisible`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx` (`searchableTarget`),
    key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx` (`oaiVisible`, `updateTime`),
    fulltext key `ezidapp_searchidentifier_resourceTitle` (`resourceTitle`),
    fulltext key `ezidapp_searchidentifier_resourceCreator` (`resourceCreator`),
    fulltext key `ezidapp_searchidentifier_resourcePublisher` (`resourcePublisher`),
    fulltext key `ezidapp_searchidentifier_keywords` (`keywords`),
    constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_searchdatacenter` (`id`),
    constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_searchprofile` (`id`),
    constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_searchgroup` (`id`),
    constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_searchuser` (`id`)
) engine = InnoDB
  auto_increment = 34228809
  default charset = utf8
  stats_sample_pages = 2000
;

##

alter table ezidapp_searchidentifier
    add column metadata json;

select count(*)
from ezidapp_searchidentifier es;
describe ezidapp_searchidentifier;

show variables where value like '%r1%';

select *
from ezidapp_shoulder es
where name like '%api%';


show engine innodb status;


select count(*)
from ezidapp_linkchecker el;

select table_rows, table_name
from information_schema.tables
where TABLE_SCHEMA = 'ezid'
  and table_name like '%_store%'
order by TABLE_NAME
;

select table_rows, table_name
from information_schema.tables
where TABLE_SCHEMA = 'ezid'
  and table_name like '%_search%'
order by TABLE_NAME
;
