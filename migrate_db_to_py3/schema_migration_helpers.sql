/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */


show engine innodb status;
show table status;
show full processlist;

kill 50;

start transaction;
rollback;
commit;

select now();


# Time of last update for any storeIdentifier (indicates when the DB was last used)
select from_unixtime(max(updatetime))
from ezidapp_storeidentifier es;


select
    ( select count(*) from ezidapp_searchidentifier) as search,
    ( select count(*) from ezidapp_storeidentifier) as store,
    ( select count(*) from ezidapp_searchidentifier es) as 'all',
    ( select count(*) from ezidapp_searchidentifier es where metadata is not null) as metadata_not_null
;


delimiter $$
drop procedure if exists drop_stubs $$
create procedure drop_stubs()
begin
  declare c int default 0;
  l1 : loop
    if (c = 10) then
      leave l1;
    end if;
    set c = c +1;
    select c;
  end loop;
end$$
delimiter ;

# Create drop statements for stub tables
# select concat_ws(' ', 'rename table', table_name, 'to', replace(table_name, '_store', '_'), ';')
# from information_schema.tables
# where table_schema = 'ezid' and table_name like 'ezidapp_store%'
# order by table_name
# ;

select concat('lock ', table_name, ' write;')
from information_schema.tables where table_schema='ezid' and table_name like 'ezidapp_%' order by table_name;

lock tables
  ezidapp_binderqueue write
, ezidapp_crossrefqueue write
, ezidapp_datacitequeue write
, ezidapp_downloadqueue write
, ezidapp_linkchecker write
, ezidapp_newaccountworksheet write
, ezidapp_registrationagency write
, ezidapp_searchdatacenter write
, ezidapp_searchgroup write
, ezidapp_searchidentifier write
, ezidapp_searchprofile write
, ezidapp_searchrealm write
, ezidapp_searchuser write
, ezidapp_servervariables write
, ezidapp_shoulder write
, ezidapp_shouldertype write
, ezidapp_statistics write
, ezidapp_storedatacenter write
, ezidapp_storegroup write
, ezidapp_storegroup_shoulders write
, ezidapp_storeidentifier write
, ezidapp_storeprofile write
, ezidapp_storerealm write
, ezidapp_storeuser write
, ezidapp_storeuser_proxies write
, ezidapp_storeuser_shoulders write
, ezidapp_updatequeue write
;

unlock tables;

###########

# Replace
# ((when \d+ then \d+ ){10})
# $1\n

# user
# 27min on RDS
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchuser a join ezidapp_storeuser b on a.pid = b.pid
order by a.id
;

# Only works in MyISAM
# alter table ezidapp_searchidentifier disable keys;

# group
select now();
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchgroup a join ezidapp_storegroup b on a.pid = b.pid
order by a.id
;

# profile
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchprofile a join ezidapp_storeprofile b on a.label = b.label
order by a.id
;

#
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchdatacenter a join ezidapp_storedatacenter b on a.symbol = b.symbol
order by a.id
;


# Check integrity of the search/store fields on which we'll be joining
# All counts should be 0.
select
    (select count(*) from ezidapp_storeuser        where pid not in    (select pid from ezidapp_searchuser )) as store_user,
    (select count(*) from ezidapp_storegroup       where pid not in    (select pid from ezidapp_searchgroup )) as store_group,
    (select count(*) from ezidapp_storeprofile     where label not in  (select label from ezidapp_searchprofile )) as store_profile,
    (select count(*) from ezidapp_storedatacenter  where symbol not in (select symbol from ezidapp_searchdatacenter )) as store_datacenter,

    (select count(*) from ezidapp_searchuser       where pid not in    (select pid from ezidapp_storeuser )) as search_user,
    (select count(*) from ezidapp_searchgroup      where pid not in    (select pid from ezidapp_storegroup )) as search_group,
    (select count(*) from ezidapp_searchprofile    where label not in  (select label from ezidapp_storeprofile )) as search_profile,
    (select count(*) from ezidapp_searchdatacenter where symbol not in (select symbol from ezidapp_storedatacenter )) as search_datacenter
;

# Check that there are no nulls.
# All counts should be 0.
select
    (select count(*) from ezidapp_searchidentifier si where si.owner_id is null) as owner,
    (select count(*) from ezidapp_searchidentifier si where si.ownergroup_id is null) as ownergroup,
    (select count(*) from ezidapp_searchidentifier si where si.profile_id is null) as `profile`,
    (select count(*) from ezidapp_searchidentifier si where si.datacenter_id is null) as datacenter
;

# Check search-to-search FKs.
# All counts should be 0 BEFORE updating to store.
select
    (select count(*) from ezidapp_searchidentifier si where si.owner_id not in (select id from ezidapp_searchuser )) as owner,
    (select count(*) from ezidapp_searchidentifier si where si.ownergroup_id not in (select id from ezidapp_searchgroup )) as ownergroup,
    (select count(*) from ezidapp_searchidentifier si where si.profile_id not in (select id from ezidapp_searchprofile )) as label,
    (select count(*) from ezidapp_searchidentifier si where si.datacenter_id not in (select id from ezidapp_searchdatacenter )) as symbol
;


update ezidapp_searchidentifier si
    join ezidapp_searchuser searchuser on searchuser.id = si.owner_id
    join ezidapp_storeuser storeuser on storeuser.pid = searchuser.pid
#     left join ezidapp_searchgroup searchgroup on searchgroup.id = si.ownergroup_id
#     left join ezidapp_storegroup storegroup on storegroup.pid = searchgroup.pid
#     left join ezidapp_searchprofile searchprofile on searchprofile.id = si.profile_id
#     left join ezidapp_storeprofile storeprofile on storeprofile.label = searchprofile.label
#     left join ezidapp_searchdatacenter searchdatacenter on searchdatacenter.id = si.datacenter_id
#     left join ezidapp_storedatacenter storedatacenter on storedatacenter.symbol = searchdatacenter.symbol
set si.owner_id      = storeuser.id
#     si.ownergroup_id = storegroup.id,
#     si.profile_id    = storeprofile.id,
#     si.datacenter_id = storedatacenter.id
where true
;

insert into ezidapp_storedatacenter(symbol, name)
select a.symbol, a.symbol from ezidapp_searchdatacenter a
where a.symbol not in (select symbol from ezidapp_storedatacenter)
;

# Check search-to-store FKs
# All counts should be 0 AFTER updating to store.
select
    (select count(*) from ezidapp_searchidentifier si where si.owner_id not in (select id from ezidapp_storeuser )) as owner,
    (select count(*) from ezidapp_searchidentifier si where si.ownergroup_id not in (select id from ezidapp_storegroup )) as ownergroup,
    (select count(*) from ezidapp_searchidentifier si where si.profile_id not in (select id from ezidapp_storeprofile )) as label,
    (select count(*) from ezidapp_searchidentifier si where si.datacenter_id not in (select id from ezidapp_storedatacenter )) as symbol
;


# Set up a fresh ezid_test_db

drop database if exists ezid_test_db;
create database ezid_test_db;
use ezid_test_db;
drop user if exists 'ezid_test_user'@'localhost';
drop user if exists 'ezid_test_user'@'%';
create user 'ezid_test_user'@'localhost' identified by 'ezid_test_pw';
grant all privileges on *.* to 'ezid_test_user'@'localhost' with grant option;
create user 'ezid_test_user'@'%' identified by 'ezid_test_pw';
grant all privileges on *.* to 'ezid_test_user'@'%' with grant option;
show databases;

# noinspection SpellCheckingInspectionForFile
create fulltext index ezidapp_searchidentifier_resourceTitle on ezidapp_searchidentifier(resourceTitle);
create fulltext index ezidapp_searchidentifier_resourceCreator on ezidapp_searchidentifier(resourceCreator);
create fulltext index ezidapp_searchidentifier_resourcePublisher on ezidapp_searchidentifier(resourcePublisher);
create fulltext index ezidapp_searchidentifier_keywords on ezidapp_searchidentifier(keywords);
# drop index ezidapp_searchidentifier_keywords on ezidapp_searchidentifier;

# Queues

select concat('drop table ', table_name, ';')
from information_schema.tables t
where table_name like 'ezidapp%queue';


#### Backups

create table bak_searchidentifier like ezidapp_searchidentifier;
insert into bak_searchidentifier
select *
from ezidapp_searchidentifier es;

create table bak_django_migrations like django_migrations;
insert bak_django_migrations
select *
from django_migrations dm;
select count(*)
from bak_django_migrations bdm;

select *
from django_migrations bdm
where app = 'ezidapp';
delete
from django_migrations
where app = 'ezidapp';
select count(*)
from django_migrations dm;


####


drop table ezidapp_binderqueue;

create table if not exists ezidapp_binderqueue (
    seq int auto_increment primary key,
    enqueuetime int not null,
    submittime int null,
    operation varchar(1) not null,
    status varchar(1) not null,
    message longtext not null,
    batchid varchar(36) not null,
    error longtext not null,
    errorispermanent tinyint(1) not null,
    refidentifier_id int not null,
    constraint ezidapp_binderqueue_refidentifier_id_50f30ec2_fk_ezidapp_r foreign key (refidentifier_id) references ezidapp_refidentifier(id)
);

create index ezidapp_binderqueue_status_55adbf21 on ezidapp_binderqueue(status);




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

delete
from test3.django_migrations dm
where dm.app = 'ezidapp';

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
alter table ezidapp_user_shoulders
change column storeuser_id user_id int;
alter table ezidapp_group_shoulders
change column storegroup_id group_id int;
alter table ezidapp_user_proxies
change column from_storeuser_id from_user_id int;
alter table ezidapp_user_proxies
change column to_storeuser_id to_user_id int;
# MariaDB
alter table ezidapp_user_shoulders rename column storeuser_id to user_id;
alter table ezidapp_group_shoulders rename column storegroup_id to group_id;
alter table ezidapp_user_proxies rename column from_storeuser_id to from_user_id;
alter table ezidapp_user_proxies rename column to_storeuser_id to to_user_id;
;

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
where referenced_table_schema = 'ezid' and referenced_table_name like 'ezidapp_%';


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


# Generate queries for dropping foreign key constraints on all ezidapp_ tables
select concat_ws(' ', 'alter table', table_name, 'drop constraint', constraint_name, ';'), table_name, column_name,
    constraint_name, referenced_table_name, referenced_column_name
from information_schema.key_column_usage
where referenced_table_schema = 'test3' and referenced_table_name like 'ezidapp_%';


select
    (select count(*) from ezidapp_searchdatacenter) as searchdatacenter,
    (select count(*) from ezidapp_storedatacenter) as storedatacenter,
    (select count(*) from ezidapp_searchgroup) as searchgroup,
    (select count(*) from ezidapp_storegroup) as storegroup,
    (select count(*) from ezidapp_searchidentifier) as searchidentifier,
    (select count(*) from ezidapp_storeidentifier) as storeidentifier,
    (select count(*) from ezidapp_searchprofile) as searchprofile,
    (select count(*) from ezidapp_storeprofile) as storeprofile,
    (select count(*) from ezidapp_searchrealm) as searchrealm,
    (select count(*) from ezidapp_storerealm) as storerealm,
    (select count(*) from ezidapp_searchuser) as searchuser,
    (select count(*) from ezidapp_storeuser) as storeuser
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
where table_schema = 'ezid' and table_name = 'ezidapp_searchdatacenter';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storedatacenter';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_searchgroup';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storegroup';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_searchidentifier';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storeidentifier';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_searchprofile';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storeprofile';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_searchrealm';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storerealm';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_searchuser';
select column_name
from information_schema.columns
where table_schema = 'ezid' and table_name = 'ezidapp_storeuser';

##

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

create table `ezidapp_searchidentifier` (
    `id` int(11) not null auto_increment,
    `identifier` varchar(255) character set ascii collate ascii_bin not null,
    `createTime` int(11) not null,
    `updateTime` int(11) not null,
    `status` varchar(1) not null,
    `unavailableReason` longtext character set utf8mb4 not null,
    `exported` tinyint(1) not null,
    `crossrefStatus` varchar(1) not null,
    `crossrefMessage` longtext character set utf8mb4 not null,
    `target` varchar(2000) not null,
    `cm` longblob not null,
    `agentRole` varchar(1) not null,
    `isTest` tinyint(1) not null,
    `owner_id` int(11) not null,
    `ownergroup_id` int(11) not null,
    `datacenter_id` int(11) default null,
    `profile_id` int(11) not null,
    `searchableTarget` varchar(255) not null,
    `resourceCreator` longtext character set utf8mb4 not null,
    `resourceTitle` longtext character set utf8mb4 not null,
    `resourcePublisher` longtext character set utf8mb4 not null,
    `resourcePublicationDate` longtext character set utf8mb4 not null,
    `searchablePublicationYear` int(11) default null,
    `resourceType` longtext character set utf8mb4 not null,
    `searchableResourceType` varchar(2) not null,
    `keywords` longtext character set utf8mb4 not null,
    `resourceCreatorPrefix` varchar(50) character set utf8mb4 not null,
    `resourceTitlePrefix` varchar(50) character set utf8mb4 not null,
    `resourcePublisherPrefix` varchar(50) character set utf8mb4 not null,
    `hasMetadata` tinyint(1) not null,
    `publicSearchVisible` tinyint(1) not null,
    `oaiVisible` tinyint(1) not null,
    `hasIssues` tinyint(1) not null,
    `linkIsBroken` tinyint(1) not null,
    primary key (`id`),
    unique key `identifier`(`identifier`),
    key `ezidapp_searchidentifier_5e7b1936`(`owner_id`),
    key `ezidapp_searchidentifier_365b2611`(`ownergroup_id`),
    key `ezidapp_searchidentifier_13bc2970`(`datacenter_id`),
    key `ezidapp_searchidentifier_83a0eb3f`(`profile_id`),
    key `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx`(`owner_id`, `identifier`),
    key `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx`(`ownergroup_id`, `identifier`),
    key `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx`(`owner_id`, `createTime`),
    key `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx`(`owner_id`, `updateTime`),
    key `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx`(`owner_id`, `status`),
    key `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx`(`owner_id`, `exported`),
    key `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx`(`owner_id`, `crossrefStatus`),
    key `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx`(`owner_id`, `profile_id`),
    key `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx`(`owner_id`, `isTest`),
    key `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx`(`owner_id`, `searchablePublicationYear`),
    key `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx`(`owner_id`, `searchableResourceType`),
    key `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx`(`owner_id`, `hasMetadata`),
    key `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx`(`owner_id`, `hasIssues`),
    key `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx`(`owner_id`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx`(`owner_id`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx`(`owner_id`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx`(`ownergroup_id`, `createTime`),
    key `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx`(`ownergroup_id`, `updateTime`),
    key `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx`(`ownergroup_id`, `status`),
    key `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx`(`ownergroup_id`, `exported`),
    key `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx`(`ownergroup_id`, `crossrefStatus`),
    key `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx`(`ownergroup_id`, `profile_id`),
    key `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx`(`ownergroup_id`, `isTest`),
    key `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx`(`ownergroup_id`, `searchablePublicationYear`),
    key `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx`(`ownergroup_id`, `searchableResourceType`),
    key `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx`(`ownergroup_id`, `hasMetadata`),
    key `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx`(`ownergroup_id`, `hasIssues`),
    key `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx`(`ownergroup_id`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx`(`ownergroup_id`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx`(`ownergroup_id`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx`(`publicSearchVisible`, `identifier`),
    key `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx`(`publicSearchVisible`, `createTime`),
    key `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx`(`publicSearchVisible`, `updateTime`),
    key `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx`(`publicSearchVisible`, `searchablePublicationYear`),
    key `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx`(`publicSearchVisible`, `searchableResourceType`),
    key `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx`(`publicSearchVisible`, `resourceCreatorPrefix`),
    key `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx`(`publicSearchVisible`, `resourceTitlePrefix`),
    key `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx`(`publicSearchVisible`, `resourcePublisherPrefix`),
    key `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx`(`searchableTarget`),
    key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx`(`oaiVisible`, `updateTime`),
    fulltext key `ezidapp_searchidentifier_resourceTitle`(`resourceTitle`),
    fulltext key `ezidapp_searchidentifier_resourceCreator`(`resourceCreator`),
    fulltext key `ezidapp_searchidentifier_resourcePublisher`(`resourcePublisher`),
    fulltext key `ezidapp_searchidentifier_keywords`(`keywords`),
    constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_searchdatacenter`(`id`),
    constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_searchprofile`(`id`),
    constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_searchgroup`(`id`),
    constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_searchuser`(`id`)
)
    engine = InnoDB
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


select count(*)
from ezidapp_linkchecker el;

select table_rows, table_name
from information_schema.tables
where table_schema = 'ezid' and table_name like '%_store%'
order by table_name
;

select table_rows, table_name
from information_schema.tables
where table_schema = 'ezid' and table_name like '%_search%'
order by table_name
;


#


create table auth_group (
    id int auto_increment primary key,
    name varchar(150) not null,
    constraint name unique (name)
);

create table auth_user (
    id int auto_increment primary key,
    password varchar(128) not null,
    last_login datetime(6) null,
    is_superuser tinyint(1) not null,
    username varchar(150) not null,
    first_name varchar(150) not null,
    last_name varchar(150) not null,
    email varchar(254) not null,
    is_staff tinyint(1) not null,
    is_active tinyint(1) not null,
    date_joined datetime(6) not null,
    constraint username unique (username)
);

create table auth_user_groups (
    id int auto_increment primary key,
    user_id int not null,
    group_id int not null,
    constraint user_id unique (user_id, group_id),
    constraint auth_user_groups_group_id_33ac548dcf5f8e37_fk_auth_group_id foreign key (group_id) references auth_group(id),
    constraint auth_user_groups_user_id_4b5ed4ffdb8fd9b0_fk_auth_user_id foreign key (user_id) references auth_user(id)
);

create table backup_ezidapp_binderqueue (
    seq int default 0 not null,
    metadata longblob not null
);

create table backup_ezidapp_crossrefqueue (
    seq int default 0 not null,
    metadata longblob not null
);

create table backup_ezidapp_datacitequeue (
    seq int default 0 not null,
    metadata longblob not null
);

create table backup_ezidapp_searchidentifier (
    id int default 0 not null,
    cm longblob not null
);

create table django_content_type (
    id int auto_increment primary key,
    app_label varchar(100) not null,
    model varchar(100) not null,
    constraint django_content_type_app_label_45f3b1d93ec8c61c_uniq unique (app_label, model)
);

create table auth_permission (
    id int auto_increment primary key,
    name varchar(255) not null,
    content_type_id int not null,
    codename varchar(100) not null,
    constraint content_type_id unique (content_type_id, codename),
    constraint auth__content_type_id_508cf46651277a81_fk_django_content_type_id foreign key (content_type_id) references django_content_type(id)
);

create table auth_group_permissions (
    id int auto_increment primary key,
    group_id int not null,
    permission_id int not null,
    constraint group_id unique (group_id, permission_id),
    constraint auth_group__permission_id_1f49ccbbdc69d2fc_fk_auth_permission_id foreign key (permission_id) references auth_permission(id),
    constraint auth_group_permission_group_id_689710a9a73b7457_fk_auth_group_id foreign key (group_id) references auth_group(id)
);

create table auth_user_user_permissions (
    id int auto_increment primary key,
    user_id int not null,
    permission_id int not null,
    constraint user_id unique (user_id, permission_id),
    constraint auth_user_u_permission_id_384b62483d7071f0_fk_auth_permission_id foreign key (permission_id) references auth_permission(id),
    constraint auth_user_user_permissi_user_id_7f0938558328534a_fk_auth_user_id foreign key (user_id) references auth_user(id)
);

create table django_admin_log (
    id int auto_increment primary key,
    action_time datetime(6) not null,
    object_id longtext null,
    object_repr varchar(200) not null,
    action_flag smallint unsigned not null,
    change_message longtext not null,
    content_type_id int null,
    user_id int not null,
    constraint djang_content_type_id_697914295151027a_fk_django_content_type_id foreign key (content_type_id) references django_content_type(id),
    constraint django_admin_log_user_id_52fdd58701c5f563_fk_auth_user_id foreign key (user_id) references auth_user(id)
);

create table django_migrations (
    id int auto_increment primary key,
    app varchar(255) not null,
    name varchar(255) not null,
    applied datetime(6) not null
);

create table django_session (
    session_key varchar(40) not null primary key,
    session_data longtext not null,
    expire_date datetime(6) not null
);

create index django_session_de54fa62 on django_session(expire_date);

create table ezidapp_binderqueue (
    seq int auto_increment primary key,
    enqueuetime int not null,
    submittime int null,
    identifier varchar(1000) not null,
    metadata longblob not null,
    owner varchar(1000) not null,
    operation varchar(1) not null,
    status varchar(1) not null,
    message longtext not null,
    batchid varchar(36) not null,
    error longtext not null,
    errorispermanent tinyint(1) not null
);

create index ezidapp_binderqueue_identifier_9b9a81d1 on ezidapp_binderqueue(identifier);

create index ezidapp_binderqueue_owner_7a7cf1d5 on ezidapp_binderqueue(owner);

create index ezidapp_binderqueue_status_55adbf21 on ezidapp_binderqueue(status);

create table ezidapp_crossrefqueue (
    seq int auto_increment primary key,
    enqueuetime int not null,
    submittime int null,
    identifier varchar(1000) not null,
    metadata longblob not null,
    owner varchar(1000) not null,
    operation varchar(1) not null,
    status varchar(1) not null,
    message longtext not null,
    batchid varchar(36) not null,
    error longtext not null,
    errorispermanent tinyint(1) not null
);

create index ezidapp_crossrefqueue_identifier_9b5a567d on ezidapp_crossrefqueue(identifier);

create index ezidapp_crossrefqueue_owner_5b61bd96 on ezidapp_crossrefqueue(owner);

create index ezidapp_crossrefqueue_status_285b2361 on ezidapp_crossrefqueue(status);

create table ezidapp_datacenter (
    id int auto_increment primary key,
    symbol varchar(17) not null,
    name varchar(255) not null,
    constraint name unique (name),
    constraint symbol unique (symbol)
);

create table ezidapp_datacitequeue (
    seq int auto_increment primary key,
    enqueuetime int not null,
    submittime int null,
    identifier varchar(1000) not null,
    metadata longblob not null,
    owner varchar(1000) not null,
    operation varchar(1) not null,
    status varchar(1) not null,
    message longtext not null,
    batchid varchar(36) not null,
    error longtext not null,
    errorispermanent tinyint(1) not null
);

create index ezidapp_datacitequeue_identifier_a6494081 on ezidapp_datacitequeue(identifier);

create index ezidapp_datacitequeue_owner_c31423b7 on ezidapp_datacitequeue(owner);

create index ezidapp_datacitequeue_status_c99416f7 on ezidapp_datacitequeue(status);

create table ezidapp_downloadqueue (
    seq int default 0 not null,
    metadata longblob not null
);

create table ezidapp_group (
    id int auto_increment primary key,
    pid varchar(255) collate ascii_bin not null,
    groupname varchar(32) not null,
    organizationname varchar(255) not null,
    organizationacronym varchar(255) not null,
    organizationurl varchar(255) not null,
    organizationstreetaddress varchar(255) not null,
    agreementonfile tinyint(1) not null,
    crossrefenabled tinyint(1) not null,
    notes longtext not null,
    realm_id int not null,
    accounttype varchar(1) not null,
    constraint groupname unique (groupname),
    constraint pid unique (pid)
);

create index ezidapp_store_realm_id_3405b66a3ee93b42_fk_ezidapp_storerealm_id on ezidapp_group(realm_id);

create table ezidapp_group_shoulders (
    id int auto_increment primary key,
    group_id int null,
    shoulder_id int not null,
    constraint storegroup_id unique (group_id, shoulder_id)
);

create index ezidapp_stor_shoulder_id_592128c84020a89a_fk_ezidapp_shoulder_id on ezidapp_group_shoulders(shoulder_id);

create table ezidapp_identifier (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    datacenter_id int null,
    owner_id int null,
    ownergroup_id int null,
    profile_id int not null,
    metadata json null,
    constraint identifier unique (identifier)
);

create index ezidapp_storeidentifier_13bc2970 on ezidapp_identifier(datacenter_id);

create index ezidapp_storeidentifier_365b2611 on ezidapp_identifier(ownergroup_id);

create index ezidapp_storeidentifier_5e7b1936 on ezidapp_identifier(owner_id);

create index ezidapp_storeidentifier_83a0eb3f on ezidapp_identifier(profile_id);

create table ezidapp_linkchecker (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    owner_id int not null,
    target varchar(2000) not null,
    lastchecktime int not null,
    numfailures int not null,
    returncode int null,
    mimetype varchar(255) not null,
    size int null,
    hash varchar(32) not null,
    isbad tinyint(1) not null,
    error longtext not null,
    constraint identifier unique (identifier)
);

create index ezidapp_linkchecker_28a3c780 on ezidapp_linkchecker(numfailures);

create index ezidapp_linkchecker_5e7b1936 on ezidapp_linkchecker(owner_id);

create index ezidapp_linkchecker_owner_id_a6cbca8ea9539b4_idx on ezidapp_linkchecker(owner_id, isbad, lastchecktime);

create table ezidapp_newaccountworksheet (
    id int auto_increment primary key,
    requestdate date not null,
    orgname varchar(255) not null,
    orgacronym varchar(255) not null,
    orgurl varchar(255) not null,
    orgstreetaddress varchar(255) not null,
    reqname varchar(255) not null,
    reqemail varchar(255) not null,
    reqphone varchar(255) not null,
    priname varchar(255) not null,
    priemail varchar(255) not null,
    priphone varchar(255) not null,
    secname varchar(255) not null,
    secemail varchar(255) not null,
    secphone varchar(255) not null,
    reqarks tinyint(1) not null,
    reqdois tinyint(1) not null,
    reqcrossref tinyint(1) not null,
    reqcrossrefemail varchar(255) not null,
    reqcomments longtext not null,
    setrealm varchar(255) not null,
    setgroupname varchar(255) not null,
    setusername varchar(255) not null,
    setnotes longtext not null,
    staready tinyint(1) not null,
    stashoulderscreated tinyint(1) not null,
    staaccountcreated tinyint(1) not null,
    accountemail varchar(255) not null,
    setnondefaultsetup tinyint(1) not null,
    setshoulderdisplayname varchar(255) not null,
    setuserdisplayname varchar(255) not null
);

create table ezidapp_profile (
    id int auto_increment primary key,
    label varchar(32) not null,
    constraint label unique (label)
);

create table ezidapp_realm (
    id int auto_increment primary key,
    name varchar(32) not null,
    constraint name unique (name)
);



drop table ezidapp_refidentifier;

create table ezid.ezidapp_refidentifier (
    id int auto_increment primary key,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext not null,
    target varchar(2000) not null,
    cm longblob not null,
    metadata json not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    identifier varchar(255) not null,
    datacenter_id int null,
    owner_id int null,
    ownergroup_id int null,
    profile_id int null,
    constraint ezidapp_refidentifie_datacenter_id_0927c7e5_fk_ezidapp_d foreign key (datacenter_id) references ezid.ezidapp_datacenter(id),
    constraint ezidapp_refidentifier_owner_id_bcf67913_fk_ezidapp_user_id foreign key (owner_id) references ezid.ezidapp_user(id),
    constraint ezidapp_refidentifier_ownergroup_id_d390fbc9_fk_ezidapp_group_id foreign key (ownergroup_id) references ezid.ezidapp_group(id),
    constraint ezidapp_refidentifier_profile_id_f497af12_fk_ezidapp_profile_id foreign key (profile_id) references ezid.ezidapp_profile(id)
);



create table ezidapp_refidentifier (
    id int auto_increment primary key,
    identifier varchar(255) not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext not null,
    target varchar(2000) not null,
    metadata json null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    constraint identifier unique (identifier)
);

create table ezidapp_registrationagency (
    id int auto_increment primary key,
    registration_agency varchar(32) not null
);

create table ezidapp_searchidentifier (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    owner_id int not null,
    ownergroup_id int not null,
    datacenter_id int null,
    profile_id int not null,
    searchabletarget varchar(255) not null,
    resourcecreator longtext charset utf8mb4 not null,
    resourcetitle longtext charset utf8mb4 not null,
    resourcepublisher longtext charset utf8mb4 not null,
    resourcepublicationdate longtext charset utf8mb4 not null,
    searchablepublicationyear int null,
    resourcetype longtext charset utf8mb4 not null,
    searchableresourcetype varchar(2) not null,
    keywords longtext charset utf8mb4 not null,
    resourcecreatorprefix varchar(50) charset utf8mb4 not null,
    resourcetitleprefix varchar(50) charset utf8mb4 not null,
    resourcepublisherprefix varchar(50) charset utf8mb4 not null,
    hasmetadata tinyint(1) not null,
    publicsearchvisible tinyint(1) not null,
    oaivisible tinyint(1) not null,
    hasissues tinyint(1) not null,
    linkisbroken tinyint(1) not null,
    metadata json null,
    constraint identifier unique (identifier)
);

create index ezidapp_searchidentifie_publicsearchvisible_47b0a294295f5ef5_idx on ezidapp_searchidentifier(publicsearchvisible, updatetime);

create index ezidapp_searchidentifier_13bc2970 on ezidapp_searchidentifier(datacenter_id);

create index ezidapp_searchidentifier_5e7b1936 on ezidapp_searchidentifier(owner_id);

create index ezidapp_searchidentifier_83a0eb3f on ezidapp_searchidentifier(profile_id);

create index ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx on ezidapp_searchidentifier(owner_id, searchablepublicationyear);

create index ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx on ezidapp_searchidentifier(ownergroup_id, resourcepublisherprefix);

create table ezidapp_servervariables (
    id int auto_increment primary key,
    alertmessage varchar(255) not null,
    secretkey varchar(50) not null
);

create table ezidapp_shoulder (
    id int auto_increment primary key,
    prefix varchar(255) collate ascii_bin not null,
    type varchar(32) not null,
    name varchar(255) not null,
    minter varchar(255) not null,
    datacenter_id int null,
    crossrefenabled tinyint(1) not null,
    istest tinyint(1) not null,
    active tinyint(1) not null,
    date date null,
    issupershoulder tinyint(1) not null,
    manager varchar(32) null,
    prefix_shares_datacenter tinyint(1) not null,
    redirect varchar(255) null,
    shoulder_type_id int null,
    registration_agency_id int null,
    constraint name unique (name, type),
    constraint prefix unique (prefix)
);

create index ezid_datacenter_id_4fb7570a75b0c69_fk_ezidapp_storedatacenter_id on ezidapp_shoulder(datacenter_id);

create index ezidapp_shoulder_registration_agency__ba15f13e_fk_ezidapp_r on ezidapp_shoulder(registration_agency_id);

create index ezidapp_shoulder_shoulder_type_id_184bbced_fk_ezidapp_s on ezidapp_shoulder(shoulder_type_id);

create table ezidapp_shouldertype (
    id int auto_increment primary key,
    shoulder_type varchar(32) not null
);

create table ezidapp_statistics (
    id int auto_increment primary key,
    month varchar(7) not null,
    owner varchar(255) collate ascii_bin not null,
    ownergroup varchar(255) collate ascii_bin not null,
    realm varchar(32) not null,
    type varchar(32) not null,
    hasmetadata tinyint(1) not null,
    count int not null,
    constraint ezidapp_statistics_month_23cad98a47c1a6fc_uniq unique (month, owner, type, hasmetadata)
);

create index ezidapp_statistics_7436f942 on ezidapp_statistics(month);

create table ezidapp_updatequeue (
    seq int default 0 not null,
    metadata longblob not null
);

create table ezidapp_user (
    id int auto_increment primary key,
    pid varchar(255) collate ascii_bin not null,
    username varchar(32) not null,
    displayname varchar(255) charset utf8mb4 not null,
    accountemail varchar(255) charset utf8mb4 not null,
    primarycontactname varchar(255) charset utf8mb4 not null,
    primarycontactemail varchar(255) charset utf8mb4 not null,
    primarycontactphone varchar(255) charset utf8mb4 not null,
    secondarycontactname varchar(255) charset utf8mb4 not null,
    secondarycontactemail varchar(255) charset utf8mb4 not null,
    secondarycontactphone varchar(255) charset utf8mb4 not null,
    inheritgroupshoulders tinyint(1) not null,
    crossrefenabled tinyint(1) not null,
    crossrefemail varchar(255) not null,
    isgroupadministrator tinyint(1) not null,
    isrealmadministrator tinyint(1) not null,
    issuperuser tinyint(1) not null,
    loginenabled tinyint(1) not null,
    password varchar(128) not null,
    notes longtext not null,
    group_id int not null,
    realm_id int not null,
    constraint pid unique (pid),
    constraint username unique (username)
);

create index ezidapp_store_group_id_7eff2039d02834ed_fk_ezidapp_storegroup_id on ezidapp_user(group_id);

create index ezidapp_store_realm_id_5d5c037d7f3fac93_fk_ezidapp_storerealm_id on ezidapp_user(realm_id);

create table ezidapp_user_proxies (
    id int auto_increment primary key,
    from_user_id int null,
    to_user_id int null,
    constraint from_storeuser_id unique (from_user_id, to_user_id)
);

create index ezidapp_storeuser_pr_to_storeuser_id_5588e255_fk_ezidapp_s on ezidapp_user_proxies(to_user_id);

create table ezidapp_user_shoulders (
    id int auto_increment primary key,
    user_id int null,
    shoulder_id int not null,
    constraint storeuser_id unique (user_id, shoulder_id)
);

create index ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id on ezidapp_user_shoulders(shoulder_id);

create table storeidentifier (
    id int not null primary key,
    meta json null
);

create table tmp_ezidapp_searchidentifier (
    id int not null primary key,
    meta json null
);

create table tmp_ezidapp_storeidentifier (
    id int not null primary key,
    meta json null
);

create table tmp_search (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    owner_id int not null,
    ownergroup_id int not null,
    datacenter_id int null,
    profile_id int not null,
    searchabletarget varchar(255) not null,
    resourcecreator longtext charset utf8mb4 not null,
    resourcetitle longtext charset utf8mb4 not null,
    resourcepublisher longtext charset utf8mb4 not null,
    resourcepublicationdate longtext charset utf8mb4 not null,
    searchablepublicationyear int null,
    resourcetype longtext charset utf8mb4 not null,
    searchableresourcetype varchar(2) not null,
    keywords longtext charset utf8mb4 not null,
    resourcecreatorprefix varchar(50) charset utf8mb4 not null,
    resourcetitleprefix varchar(50) charset utf8mb4 not null,
    resourcepublisherprefix varchar(50) charset utf8mb4 not null,
    hasmetadata tinyint(1) not null,
    publicsearchvisible tinyint(1) not null,
    oaivisible tinyint(1) not null,
    hasissues tinyint(1) not null,
    linkisbroken tinyint(1) not null,
    metadata json null
);

create table tmp_si (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    owner_id int not null,
    ownergroup_id int not null,
    datacenter_id int null,
    profile_id int not null,
    searchabletarget varchar(255) not null,
    resourcecreator longtext charset utf8mb4 not null,
    resourcetitle longtext charset utf8mb4 not null,
    resourcepublisher longtext charset utf8mb4 not null,
    resourcepublicationdate longtext charset utf8mb4 not null,
    searchablepublicationyear int null,
    resourcetype longtext charset utf8mb4 not null,
    searchableresourcetype varchar(2) not null,
    keywords longtext charset utf8mb4 not null,
    resourcecreatorprefix varchar(50) charset utf8mb4 not null,
    resourcetitleprefix varchar(50) charset utf8mb4 not null,
    resourcepublisherprefix varchar(50) charset utf8mb4 not null,
    hasmetadata tinyint(1) not null,
    publicsearchvisible tinyint(1) not null,
    oaivisible tinyint(1) not null,
    hasissues tinyint(1) not null,
    linkisbroken tinyint(1) not null,
    metadata json null,
    constraint identifier unique (identifier)
);


create table tmp_si2 (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    owner_id int not null,
    ownergroup_id int not null,
    datacenter_id int null,
    profile_id int not null,
    searchabletarget varchar(255) not null,
    resourcecreator longtext charset utf8mb4 not null,
    resourcetitle longtext charset utf8mb4 not null,
    resourcepublisher longtext charset utf8mb4 not null,
    resourcepublicationdate longtext charset utf8mb4 not null,
    searchablepublicationyear int null,
    resourcetype longtext charset utf8mb4 not null,
    searchableresourcetype varchar(2) not null,
    keywords longtext charset utf8mb4 not null,
    resourcecreatorprefix varchar(50) charset utf8mb4 not null,
    resourcetitleprefix varchar(50) charset utf8mb4 not null,
    resourcepublisherprefix varchar(50) charset utf8mb4 not null,
    hasmetadata tinyint(1) not null,
    publicsearchvisible tinyint(1) not null,
    oaivisible tinyint(1) not null,
    hasissues tinyint(1) not null,
    linkisbroken tinyint(1) not null,
    metadata json null
);

create table tmp_stid (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    datacenter_id int null,
    owner_id int null,
    ownergroup_id int null,
    profile_id int not null,
    metadata json null,
    constraint identifier unique (identifier)
);

create index ezidapp_storeidentifier_13bc2970 on tmp_stid(datacenter_id);

create index ezidapp_storeidentifier_365b2611 on tmp_stid(ownergroup_id);

create index ezidapp_storeidentifier_5e7b1936 on tmp_stid(owner_id);

create index ezidapp_storeidentifier_83a0eb3f on tmp_stid(profile_id);

create table tmp_stid2 (
    id int auto_increment primary key,
    identifier varchar(255) collate ascii_bin not null,
    createtime int not null,
    updatetime int not null,
    status varchar(1) not null,
    unavailablereason longtext charset utf8mb4 not null,
    exported tinyint(1) not null,
    crossrefstatus varchar(1) not null,
    crossrefmessage longtext charset utf8mb4 not null,
    target varchar(2000) not null,
    cm longblob not null,
    agentrole varchar(1) not null,
    istest tinyint(1) not null,
    datacenter_id int null,
    owner_id int null,
    ownergroup_id int null,
    profile_id int not null,
    metadata json null,
    constraint identifier unique (identifier)
);

create index ezidapp_storeidentifier_13bc2970 on tmp_stid2(datacenter_id);

create index ezidapp_storeidentifier_365b2611 on tmp_stid2(ownergroup_id);

create index ezidapp_storeidentifier_5e7b1936 on tmp_stid2(owner_id);

create index ezidapp_storeidentifier_83a0eb3f on tmp_stid2(profile_id);
