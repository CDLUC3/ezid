/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

use ezid;

show engine innodb status;
show table status;
show full processlist;
select version();

kill 50;

set @@autocommit = 0;
start transaction;
rollback;
commit;

select now();
select max(id) from ezidapp_searchidentifier;

# Time of last update for any storeIdentifier (indicates when the DB was last used)
select from_unixtime(max(updatetime))
from ezidapp_storeidentifier es;

# MySQL [ezid]> show global variables like 'innodb_buffer%';
# +-------------------------------------+----------------+
# | Variable_name                       | Value          |
# +-------------------------------------+----------------+
# | innodb_buffer_pool_chunk_size       | 134217728      |
# | innodb_buffer_pool_dump_at_shutdown | ON             |
# | innodb_buffer_pool_dump_now         | OFF            |
# | innodb_buffer_pool_dump_pct         | 25             |
# | innodb_buffer_pool_filename         | ib_buffer_pool |
# | innodb_buffer_pool_instances        | 8              |
# | innodb_buffer_pool_load_abort       | OFF            |
# | innodb_buffer_pool_load_at_startup  | ON             |
# | innodb_buffer_pool_load_now         | OFF            |
# | innodb_buffer_pool_size             | 1073741824     |
# +-------------------------------------+----------------+
# 10 rows in set (0.09 sec)

select
    ( select count(*) from ezidapp_searchidentifier) as search,
    ( select count(*) from ezidapp_storeidentifier) as store,
    ( select count(*) from ezidapp_searchidentifier es) as 'all',
    ( select count(*) from ezidapp_searchidentifier es where metadata is not null) as metadata_not_null
;

# List all constraints
select constraint_name,
       unique_constraint_name,
       match_option,
       update_rule,
       delete_rule,
       table_name,
       referenced_table_name
from information_schema.referential_constraints
where constraint_schema = 'ezid'
;

# Template for counter loop in stored procedure
delimiter $$
drop procedure if exists drop_stubs $$
create procedure drop_stubs()
begin
  declare c int default 0;
  l1 : loop
    if (c = 10) then
      leave l1;
    end if;
    set c = c + 1;
    select c;
  end loop;
end$$
delimiter ;


select column_name
from
  information_schema.key_column_usage
where
    table_name = 'ezidapp_searchidentifier'
    and constraint_schema = 'ezid'
;




alter table ezidapp_searchidentifier
drop key ezidapp_searchidentifier_keywords;
alter table ezidapp_searchidentifier
drop key ezidapp_searchidentifier_resourcecreator;
alter table ezidapp_searchidentifier
drop key ezidapp_searchidentifier_resourcepublisher;
alter table ezidapp_searchidentifier
drop key ezidapp_searchidentifier_resourcetitle;

select match (keywords) against ('water') from ezidapp_searchidentifier es group by es.keywords with rollup ;

select keywords from ezidapp_searchidentifier limit 100;


###############


select count(*) from ezidapp_searchidentifier es group by es.hasissues;
# select count(*) from ezidapp_searchidentifier es group by es.;

select count(*) from ezidapp_linkchecker el;
select * from ezidapp_linkchecker el;


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

############

# Generate queries to drop constraints
select concat('alter table ', table_name, ' drop foreign key ', constraint_name, ';')
from information_schema.referential_constraints
where constraint_schema = 'ezid'
;

alter table auth_group_permissions drop foreign key auth_group__permission_id_1f49ccbbdc69d2fc_fk_auth_permission_id;
alter table auth_group_permissions drop foreign key auth_group_permission_group_id_689710a9a73b7457_fk_auth_group_id;
alter table auth_permission drop foreign key auth__content_type_id_508cf46651277a81_fk_django_content_type_id;
alter table auth_user_groups drop foreign key auth_user_groups_group_id_33ac548dcf5f8e37_fk_auth_group_id;
alter table auth_user_groups drop foreign key auth_user_groups_user_id_4b5ed4ffdb8fd9b0_fk_auth_user_id;
alter table auth_user_user_permissions drop foreign key auth_user_u_permission_id_384b62483d7071f0_fk_auth_permission_id;
alter table auth_user_user_permissions drop foreign key auth_user_user_permissi_user_id_7f0938558328534a_fk_auth_user_id;
alter table django_admin_log drop foreign key djang_content_type_id_697914295151027a_fk_django_content_type_id;
alter table django_admin_log drop foreign key django_admin_log_user_id_52fdd58701c5f563_fk_auth_user_id;
alter table ezidapp_searchgroup drop foreign key ezidapp_sear_realm_id_58cd72178e312e42_fk_ezidapp_searchrealm_id;
alter table ezidapp_searchuser drop foreign key ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id;
alter table ezidapp_searchuser drop foreign key ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id;
alter table ezidapp_shoulder drop foreign key ezid_datacenter_id_4fb7570a75b0c69_fk_ezidapp_storedatacenter_id;
alter table ezidapp_shoulder drop foreign key ezidapp_shoulder_registration_agency__ba15f13e_fk_ezidapp_r;
alter table ezidapp_shoulder drop foreign key ezidapp_shoulder_shoulder_type_id_184bbced_fk_ezidapp_s;
alter table ezidapp_storegroup drop foreign key ezidapp_store_realm_id_3405b66a3ee93b42_fk_ezidapp_storerealm_id;
alter table ezidapp_storegroup_shoulders drop foreign key ezidapp__storegroup_id_59e419f89a47aef8_fk_ezidapp_storegroup_id;
alter table ezidapp_storegroup_shoulders drop foreign key ezidapp_stor_shoulder_id_592128c84020a89a_fk_ezidapp_shoulder_id;
alter table ezidapp_storeidentifier drop foreign key ezi_datacenter_id_3bc5951853d0443c_fk_ezidapp_storedatacenter_id;
alter table ezidapp_storeidentifier drop foreign key ezidapp__ownergroup_id_10bf8aa5ea27b4bd_fk_ezidapp_storegroup_id;
alter table ezidapp_storeidentifier drop foreign key ezidapp_s_profile_id_4105f1929b18ac77_fk_ezidapp_storeprofile_id;
alter table ezidapp_storeidentifier drop foreign key ezidapp_storei_owner_id_2a042b1b01e4a83b_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser drop foreign key ezidapp_store_group_id_7eff2039d02834ed_fk_ezidapp_storegroup_id;
alter table ezidapp_storeuser drop foreign key ezidapp_store_realm_id_5d5c037d7f3fac93_fk_ezidapp_storerealm_id;
alter table ezidapp_storeuser_proxies drop foreign key ezida_from_storeuser_id_199e0c23a1cd56a7_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser_proxies drop foreign key ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser_shoulders drop foreign key ezidapp_st_storeuser_id_6730d06357e88738_fk_ezidapp_storeuser_id;
alter table ezidapp_storeuser_shoulders drop foreign key ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id;

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

############################

use ezid;
use ezid_test_db;

#########

select * from ezidapp_searchidentifier es;

select * from ezidapp_searchidentifier es;

describe ezidapp_searchidentifier;

select count(*) from ezidapp_searchidentifier es group by metadata is null;
select count(*) from tmp_ezidapp_storeidentifier tes group by metadata is null;

select identifier from ezidapp_searchidentifier es join user

############

delete from ezidapp_searchidentifier
where owner_id not in (select id from ezidapp_user)
;

delete from ezidapp_searchidentifier
where datacenter_id not in (select id from ezidapp_datacenter)
;

select count(*)
from ezidapp_searchidentifier
where owner_id not in (select id from ezidapp_user)
;

select * from ezid_test_db.auth_permission ap;

##########

drop table tmpuser;
create table tmpuser (
    id int,
    pid varchar(1000)
);

insert into tmpuser (id, pid)
values
    (1, 'ark:/99166/p9kw57h4w'),
    (2, 'ark:/99166/p9jq0st8j'),
    (10, 'ark:/99166/p90v89j36'),
    (13, 'ark:/99166/p9183428t'),
    (14, 'ark:/99166/p91g0hv2q'),
    (21, 'ark:/99166/p9251fm3t'),
    (26, 'ark:/99166/p92f7jr0f'),
    (28, 'ark:/99166/p92j6839m'),
    (30, 'ark:/99166/p92v2c886'),
    (31, 'ark:/99166/p92v2c89p'),
    (39, 'ark:/99166/p93j3915c'),
    (40, 'ark:/99166/p93n20h05'),
    (48, 'ark:/99166/p9542j790'),
    (52, 'ark:/99166/p95x25c19'),
    (53, 'ark:/99166/p95x25d27'),
    (69, 'ark:/99166/p9804xj8d'),
    (75, 'ark:/99166/p98g8fk30'),
    (80, 'ark:/99166/p9930nv03'),
    (89, 'ark:/99166/p99w09123'),
    (93, 'ark:/99166/p9b56d64w'),
    (96, 'ark:/99166/p9b853m08'),
    (99, 'ark:/99166/p9bn9x34q'),
    (101, 'ark:/99166/p9br8mg33'),
    (102, 'ark:/99166/p9bv79x5t'),
    (104, 'ark:/99166/p9c824g40'),
    (108, 'ark:/99166/p9cv4bs44'),
    (111, 'ark:/99166/p9df6k49v'),
    (114, 'ark:/99166/p9dv1cp1x'),
    (116, 'ark:/99166/p9f18sg88'),
    (117, 'ark:/99166/p9f47gw6m'),
    (118, 'ark:/99166/p9ff3m244'),
    (119, 'ark:/99166/p9fj29d32'),
    (120, 'ark:/99166/p9fn10t6t'),
    (123, 'ark:/99166/p9fq9q76m'),
    (124, 'ark:/99166/p9ft8dj4m'),
    (126, 'ark:/99166/p9g15tb1p'),
    (130, 'ark:/99166/p9gq6r32g'),
    (131, 'ark:/99166/p9gt5fg5s'),
    (135, 'ark:/99166/p9h12v82v'),
    (136, 'ark:/99166/p9h41jm7p'),
    (137, 'ark:/99166/p9h41jp25'),
    (139, 'ark:/99166/p9h98zc6d'),
    (140, 'ark:/99166/p9h98zg39'),
    (145, 'ark:/99166/p9hq3s13n'),
    (152, 'ark:/99166/p9jd4pn9z'),
    (159, 'ark:/99166/p9k35md9k'),
    (160, 'ark:/99166/p9k35mg61'),
    (166, 'ark:/99166/p9kw57k8q'),
    (171, 'ark:/99166/p9mc8rg4x'),
    (173, 'ark:/99166/p9mg7fv6r'),
    (175, 'ark:/99166/p9mk6591h'),
    (180, 'ark:/99166/p9nv9998r'),
    (186, 'ark:/99166/p9pn8xf6w'),
    (187, 'ark:/99166/p9pn8xh1c'),
    (188, 'ark:/99166/p9pz51k8v'),
    (191, 'ark:/99166/p9q52ff4b'),
    (192, 'ark:/99166/p9q52ff7s'),
    (193, 'ark:/99166/p9qb9v75g'),
    (195, 'ark:/99166/p9qf8jk1z'),
    (199, 'ark:/99166/p9qv3c40t'),
    (204, 'ark:/99166/p9r20rz3t'),
    (206, 'ark:/99166/p9r785p4f'),
    (207, 'ark:/99166/p9rb6w21w'),
    (210, 'ark:/99166/p9rj48x1z'),
    (211, 'ark:/99166/p9rr1pm86'),
    (213, 'ark:/99166/p9rx93d3t'),
    (214, 'ark:/99166/p9s46h63b'),
    (216, 'ark:/99166/p9sb3wx94'),
    (219, 'ark:/99166/p9sj19t2p'),
    (222, 'ark:/99166/p9st7dz94'),
    (225, 'ark:/99166/p9t43j35j'),
    (227, 'ark:/99166/p9t727g3f'),
    (228, 'ark:/99166/p9t727j2v'),
    (229, 'ark:/99166/p9tb0xv0g'),
    (230, 'ark:/99166/p9td9n725'),
    (232, 'ark:/99166/p9td9nb11'),
    (235, 'ark:/99166/p9tx3557s'),
    (236, 'ark:/99166/p9v11vk0n'),
    (237, 'ark:/99166/p9v11vk6j'),
    (239, 'ark:/99166/p9v40k03t'),
    (241, 'ark:/99166/p9v40k18p'),
    (244, 'ark:/99166/p9v698c2n'),
    (245, 'ark:/99166/p9v97zs0m'),
    (246, 'ark:/99166/p9vh5cj8m'),
    (249, 'ark:/99166/p9w08wj9k'),
    (252, 'ark:/99166/p9wh2dd5z'),
    (261, 'ark:/99166/p9z02z927'),
    (268, 'ark:/99166/p9z892h70'),
    (269, 'ark:/99166/p9cc0tw5d'),
    (271, 'ark:/99166/p92v2cc91'),
    (272, 'ark:/99166/p9td9nb30'),
    (276, 'ark:/99166/p98g8fm00'),
    (277, 'ark:/99166/p9pg1hr15'),
    (279, 'ark:/99166/p9h70834v'),
    (281, 'ark:/99166/p9th8bq4b'),
    (282, 'ark:/99166/p9x921m98'),
    (284, 'ark:/99166/p9b853m46'),
    (285, 'ark:/99166/p9gb1xk62'),
    (286, 'ark:/99166/p9w950r23'),
    (287, 'ark:/99166/p9js9hb3n'),
    (290, 'ark:/99166/p9v11vp2z'),
    (292, 'ark:/99166/p9g44ht3v'),
    (297, 'ark:/99166/p97d2q99b'),
    (298, 'ark:/99166/p9mc8rk1t'),
    (300, 'ark:/99166/p9dj58k65'),
    (307, 'ark:/99166/p9g44ht5t'),
    (308, 'ark:/99166/p9pk07499'),
    (309, 'ark:/99166/p9dz03470'),
    (310, 'ark:/99166/p99z90f8r'),
    (311, 'ark:/99166/p9vt1gs8k'),
    (316, 'ark:/99166/p9qf8jn68'),
    (320, 'ark:/99166/p93b5wb73'),
    (323, 'ark:/99166/p9x63b82g'),
    (324, 'ark:/99166/p94q7qt18'),
    (326, 'ark:/99166/p9v97zv5x'),
    (327, 'ark:/99166/p94f1mn1r'),
    (328, 'ark:/99166/p9vx0662d'),
    (333, 'ark:/99166/p9m03z12x'),
    (334, 'ark:/99166/p9sf2mf8q'),
    (337, 'ark:/99166/p9pr7mx63'),
    (338, 'ark:/99166/p9mk65c1d'),
    (340, 'ark:/99166/p9r785s4s'),
    (342, 'ark:/99166/p9gx44z0k'),
    (344, 'ark:/99166/p90r9m72r'),
    (345, 'ark:/99166/p9gh9bd14'),
    (349, 'ark:/99166/p9df6k65t'),
    (350, 'ark:/99166/p96q1sm3q'),
    (351, 'ark:/99166/p9x34mw07'),
    (354, 'ark:/99166/p9dn4003f'),
    (358, 'ark:/99166/p9b853n16'),
    (359, 'ark:/99166/p9348gk7b'),
    (361, 'ark:/99166/p94t6f67f'),
    (362, 'ark:/99166/p98s4js8x'),
    (363, 'ark:/99166/p9j38kn0s'),
    (365, 'ark:/99166/p9ww7737h'),
    (366, 'ark:/99166/p9rj48z6t'),
    (371, 'ark:/99166/p98s4js9d'),
    (372, 'ark:/99166/p9cj87q2f'),
    (375, 'ark:/99166/p9q814w7j'),
    (378, 'ark:/99166/p9w669c84'),
    (379, 'ark:/99166/p9kk94g72'),
    (386, 'ark:/99166/p9s46hb53'),
    (387, 'ark:/99166/p91c1tm34'),
    (388, 'ark:/99166/p96w96f36'),
    (389, 'ark:/99166/p92j6891f'),
    (390, 'ark:/99166/p9gx4506b'),
    (391, 'ark:/99166/p9bv7b143'),
    (392, 'ark:/99166/p9p26q84k'),
    (393, 'ark:/99166/p9v11vr4t'),
    (394, 'ark:/99166/p90863b5c'),
    (395, 'ark:/99166/p9m03z34s'),
    (396, 'ark:/99166/p9sj19x3h'),
    (397, 'ark:/99166/p93t9dc54'),
    (398, 'ark:/99166/p9pc2tf8k'),
    (399, 'ark:/99166/p93f4kt6t'),
    (400, 'ark:/99166/p9p55dp1f'),
    (401, 'ark:/99166/p9hh6cc0s'),
    (402, 'ark:/99166/p9707wv1g'),
    (403, 'ark:/99166/p9377617h'),
    (404, 'ark:/99166/p9bk16v9k'),
    (406, 'ark:/99166/p9833n46d'),
    (407, 'ark:/99166/p94b2xb28'),
    (408, 'ark:/99166/p9vt1gw21'),
    (409, 'ark:/99166/p9jd4pv9n'),
    (410, 'ark:/99166/p9cn6z53q'),
    (411, 'ark:/99166/p93776180'),
    (415, 'ark:/99166/p96t0h26b'),
    (416, 'ark:/99166/p9x921q7n'),
    (417, 'ark:/99166/p9sj19x5g'),
    (418, 'ark:/99166/p9z60c771'),
    (419, 'ark:/99166/p91z4202g'),
    (420, 'ark:/99166/p9rf5kn0z'),
    (422, 'ark:/99166/p9mk65f57'),
    (423, 'ark:/99166/p9kk94j50'),
    (424, 'ark:/99166/p95d8nm58'),
    (426, 'ark:/99166/p9j960g57'),
    (427, 'ark:/99166/p9zc7s11s'),
    (428, 'ark:/99166/p9tm7266x'),
    (429, 'ark:/99166/p9pv6bd19'),
    (430, 'ark:/99166/p9k35mk8b'),
    (431, 'ark:/99166/p9nv99h31'),
    (432, 'ark:/99166/p9j67931f'),
    (433, 'ark:/99166/p92z12w29'),
    (434, 'ark:/99166/p9sj19x6z'),
    (435, 'ark:/99166/p96m3392n'),
    (436, 'ark:/99166/p9x34mz23'),
    (437, 'ark:/99166/p9fq9qb8x'),
    (438, 'ark:/99166/p9416t545'),
    (439, 'ark:/99166/p9j38kq15'),
    (440, 'ark:/99166/p9c824m58'),
    (441, 'ark:/99166/p97h1dt14'),
    (443, 'ark:/99166/p9z02zf9d'),
    (444, 'ark:/99166/p9sb3x497'),
    (445, 'ark:/99166/p9gt5fn2k'),
    (446, 'ark:/99166/p9ww7758w'),
    (447, 'ark:/99166/p9mc8rn83'),
    (448, 'ark:/99166/p99z90j5n'),
    (449, 'ark:/99166/p96688r1t'),
    (450, 'ark:/99166/p91g0j15t'),
    (451, 'ark:/99166/p91c1tn42'),
    (452, 'ark:/99166/p9qv3c93h'),
    (453, 'ark:/99166/p98p5vg5h'),
    (454, 'ark:/99166/p94x54p1r'),
    (455, 'ark:/99166/p9d795h4g'),
    (456, 'ark:/99166/p98k75332'),
    (457, 'ark:/99166/p94t6f90d'),
    (458, 'ark:/99166/p9125qg6z'),
    (459, 'ark:/99166/p93t9dc92'),
    (460, 'ark:/99166/p9028pk6q'),
    (461, 'ark:/99166/p9tb0z19g'),
    (462, 'ark:/99166/p9hx15x4n'),
    (463, 'ark:/99166/p9z02zg0h'),
    (464, 'ark:/99166/p9794114s'),
    (465, 'ark:/99166/p92j68b0d'),
    (466, 'ark:/99166/p9s17t01r'),
    (468, 'ark:/99166/p9bv7b22k'),
    (469, 'ark:/99166/p9xp6v923'),
    (470, 'ark:/99166/p9280551c'),
    (471, 'ark:/99166/p9qv3c940'),
    (472, 'ark:/99166/p99k4602t'),
    (473, 'ark:/99166/p9222rc5q'),
    (474, 'ark:/99166/p9rn30f0j'),
    (475, 'ark:/99166/p9mw28m6s'),
    (476, 'ark:/99166/p9cc0v08m'),
    (477, 'ark:/99166/p9vd6pb42'),
    (478, 'ark:/99166/p9g44hx2q')
;

select count(*) from tmpuser e;
select count(*) from ezidapp_user eu;
select eu.id, eu.id, eu.pid
from ezidapp_user eu
         join tmpuser e on eu.pid = e.pid;

#########

delete from ezidapp_statistics where month not regexp '^(2018|2019|2020|2021)-';

###########

select count(*) from ezidapp_linkchecker el;

delete from ezidapp_linkchecker where identifier not in (select identifier from ezidapp_identifier);

# Checked if it was faster to delete in chunks, but it didn't seem to be.

drop procedure if exists clean_linkchecker;

create procedure clean_linkchecker()
begin
    declare c int;
    x:
    loop
        delete
        from ezidapp_linkchecker el
        where identifier not in (select identifier from ezidapp_identifier)
        limit 10000;

        set c = row_count();

        select concat('rows deleted: ', c) as 'debug: ';
        select concat('rows remaining: ', (select count(*) from ezidapp_linkchecker)) as 'debug: ';

        if (c = 0) then leave x; end if;
    end loop;
end;

call clean_linkchecker();

#########

drop table ezidapp_downloadqueue;

create table ezidapp_downloadqueue (
    seq int auto_increment primary key,
    enqueueTime int not null,
    submitTime int null,
    operation varchar(1) not null,
    status varchar(1) not null,
    message longtext not null,
    batchId varchar(36) not null,
    error longtext not null,
    errorIsPermanent tinyint(1) not null,
    refIdentifier_id int not null,
    requestTime int not null,
    rawRequest longtext not null,
    requestor varchar(255) not null,
    format varchar(1) not null,
    compression varchar(1) not null,
    columns longtext not null,
    constraints longtext not null,
    options longtext not null,
    notify longtext not null,
    stage varchar(1) not null,
    filename varchar(1) not null,
    toHarvest longtext not null,
    currentIndex int not null,
    lastId varchar(255) not null,
    fileSize bigint not null
)
    charset = utf8mb4;

create index ezidapp_searchindexe_refIdentifier_id_7b72d1a2_fk_ezidapp_r on ezidapp_downloadqueue(refIdentifier_id);

create index ezidapp_searchindexerqueue_operation_577fd676 on ezidapp_downloadqueue(operation);

create index ezidapp_searchindexerqueue_status_9aeeb55e on ezidapp_downloadqueue(status);

#

alter table ezid.ezidapp_downloadqueue
add requestTime int not null;

alter table ezid.ezidapp_downloadqueue
add rawRequest longtext not null;

alter table ezid.ezidapp_downloadqueue
add requestor varchar(255) not null;

alter table ezid.ezidapp_downloadqueue
add format varchar(1) not null;

alter table ezid.ezidapp_downloadqueue
add compression varchar(1) not null;

alter table ezid.ezidapp_downloadqueue
add columns longtext not null;

alter table ezid.ezidapp_downloadqueue
add columns longtext not null;

alter table ezid.ezidapp_downloadqueue
add constraints longtext not null;

alter table ezid.ezidapp_downloadqueue
add options longtext not null;

alter table ezid.ezidapp_downloadqueue
add notify longtext not null;

alter table ezid.ezidapp_downloadqueue
add stage varchar(1) not null;

alter table ezid.ezidapp_downloadqueue
add filename varchar(1) not null;

alter table ezid.ezidapp_downloadqueue
add toHarvest longtext not null;

alter table ezid.ezidapp_downloadqueue
add currentIndex int not null;

alter table ezid.ezidapp_downloadqueue
add lastId varchar(255) not null;

alter table ezid.ezidapp_downloadqueue
add fileSize bigint not null;

#############

select (select count(*) from ezidapp_searchidentifier es) as 'search',
    (select count(*) from ezidapp_searchidentifier es where metadata is not null) as 'search_metadata',
        (select count(*) from ezidapp_identifier es) as 'store',
        (select count(*) from ezidapp_identifier es where metadata is not null) as 'store_metadata'
;

select count(*) from ezidapp_searchidentifier es where rand() < 0.01;

select count(*) from ezidapp_identifier ei where ei.identifier in (select identifier from ezidapp_searchidentifier es);

delete from ezidapp_searchidentifier es where rand() > 0.1;

delete from ezidapp_identifier ei where ei.identifier not in (select identifier from ezidapp_searchidentifier es);

select sum(length(cm)) from ezidapp_searchidentifier es;

# LinkChecker

select count(*) from ezidapp_linkchecker el;
select * from ezidapp_linkchecker el;

delete from ezidapp_linkchecker el where el.identifier not in (select identifier from ezidapp_searchidentifier es);

update ezidapp_searchidentifier set metadata = '{}' where 1 = 1;
update ezidapp_identifier set metadata = '{}' where 1 = 1;

#####################3

--
-- Alter field datacenter on identifier
--
update `ezidapp_identifier` set `datacenter_id` = 'NULL' where `datacenter_id` is null;
alter table `ezidapp_identifier`
modify `datacenter_id` integer not null;
--
-- Alter field owner on identifier
--
update `ezidapp_identifier` set `owner_id` = b'NULL' where `owner_id` is null;
alter table `ezidapp_identifier`
modify `owner_id` integer not null;
--
-- Alter field ownergroup on identifier
--
update `ezidapp_identifier` set `ownergroup_id` = b'NULL' where `ownergroup_id` is null;
alter table `ezidapp_identifier`
modify `ownergroup_id` integer not null;
--
-- Alter field profile on identifier
--
update `ezidapp_identifier` set `profile_id` = b'NULL' where `profile_id` is null;
alter table `ezidapp_identifier`
modify `profile_id` integer not null;
--
-- Alter field datacenter on refidentifier
--
alter table `ezidapp_refidentifier`
drop foreign key `ezidapp_refidentifie_datacenter_id_0927c7e5_fk_ezidapp_d`;
update `ezidapp_refidentifier` set `datacenter_id` = b'NULL' where `datacenter_id` is null;
alter table `ezidapp_refidentifier`
modify `datacenter_id` integer not null;
alter table `ezidapp_refidentifier`
add constraint `ezidapp_refidentifie_datacenter_id_0927c7e5_fk_ezidapp_d` foreign key (`datacenter_id`) references `ezidapp_datacenter`(`id`);
--
-- Alter field owner on refidentifier
--
alter table `ezidapp_refidentifier`
drop foreign key `ezidapp_refidentifier_owner_id_bcf67913_fk_ezidapp_user_id`;
update `ezidapp_refidentifier` set `owner_id` = b'NULL' where `owner_id` is null;
alter table `ezidapp_refidentifier`
modify `owner_id` integer not null;
alter table `ezidapp_refidentifier`
add constraint `ezidapp_refidentifier_owner_id_bcf67913_fk_ezidapp_user_id` foreign key (`owner_id`) references `ezidapp_user`(`id`);
--
-- Alter field ownergroup on refidentifier
--
alter table `ezidapp_refidentifier`
drop foreign key `ezidapp_refidentifier_ownergroup_id_d390fbc9_fk_ezidapp_group_id`;
update `ezidapp_refidentifier` set `ownergroup_id` = b'NULL' where `ownergroup_id` is null;
alter table `ezidapp_refidentifier`
modify `ownergroup_id` integer not null;
alter table `ezidapp_refidentifier`
add constraint `ezidapp_refidentifier_ownergroup_id_d390fbc9_fk_ezidapp_group_id` foreign key (`ownergroup_id`) references `ezidapp_group`(`id`);
--
-- Alter field profile on refidentifier
--
alter table `ezidapp_refidentifier`
drop foreign key `ezidapp_refidentifier_profile_id_f497af12_fk_ezidapp_profile_id`;
update `ezidapp_refidentifier` set `profile_id` = b'NULL' where `profile_id` is null;
alter table `ezidapp_refidentifier`
modify `profile_id` integer not null;
alter table `ezidapp_refidentifier`
add constraint `ezidapp_refidentifier_profile_id_f497af12_fk_ezidapp_profile_id` foreign key (`profile_id`) references `ezidapp_profile`(`id`);
--
-- Alter field datacenter on searchidentifier
--
update `ezidapp_searchidentifier` set `datacenter_id` = b'NULL' where `datacenter_id` is null;
alter table `ezidapp_searchidentifier`
modify `datacenter_id` integer not null;
--
-- Alter field owner on searchidentifier
--
update `ezidapp_searchidentifier` set `owner_id` = b'NULL' where `owner_id` is null;
alter table `ezidapp_searchidentifier`
modify `owner_id` integer not null;
--
-- Alter field ownergroup on searchidentifier
--
update `ezidapp_searchidentifier` set `ownergroup_id` = b'NULL' where `ownergroup_id` is null;
alter table `ezidapp_searchidentifier`
modify `ownergroup_id` integer not null;
--
-- Alter field profile on searchidentifier
--
update `ezidapp_searchidentifier` set `profile_id` = b'NULL' where `profile_id` is null;
alter table `ezidapp_searchidentifier`
modify `profile_id` integer not null;


# MySQL [ezid]> select count_star, index_name from performance_schema.table_io_waits_summary_by_index_usage where object_name='ezidapp_searchidentifier' group by count_star, index_name order by count_star desc;
# +------------+------------------------------------------------------------------+
# | count_star | index_name                                                       |
# +------------+------------------------------------------------------------------+
# | 8137470925 | identifier                                                       |
# | 1694234344 | ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx |
# | 1470014804 | ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx         |
# |  211448890 | ezidapp_searchidentifier_5e7b1936                                |
# |   93001201 | ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx           |
# |   84129679 | ezidapp_searchidentifier_365b2611                                |
# |   81640063 | ezidapp_searchidentifier_13bc2970                                |
# |   71055879 | ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx           |
# |   64647693 | ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx |
# |   60195608 | ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx |
# |   59627193 | ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx           |
# |   30770472 | ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx           |
# |   27213349 | ezidapp_searchidentifier_83a0eb3f                                |
# |   23410277 | ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx      |
# |   19388568 | ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx           |
# |   14880395 | ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx           |
# |   14274173 | ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx      |
# |   14193439 | ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx      |
# |   11497247 | ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx      |
# |    5411586 | ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx           |
# |    4652160 | ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx      |
# |    4298890 | ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx      |
# |    3779471 | ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx      |
# |    3023677 | ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx           |
# |    3001925 | ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx           |
# |    2991637 | ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx      |
# |    2549026 | ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx           |
# |    2066398 | PRIMARY                                                          |
# |    1600118 | ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx           |
# |     747300 | ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx      |
# |     525993 | NULL                                                             |
# |      86164 | ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx           |
# |      35588 | ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx      |
# |       5492 | ezidapp_searchidentifier_owner_id_18a46334256a7530_idx           |
# |       4718 | ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx |
# |          4 | ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx   |
# |          0 | ezidapp_searchidentifier_keywords                                |
# |          0 | ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx      |
# |          0 | ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx      |
# |          0 | ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx      |
# |          0 | ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx       |
# |          0 | ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx      |
# |          0 | ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx           |
# |          0 | ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx           |
# |          0 | ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx |
# |          0 | ezidapp_searchidentifier_resourceCreator                         |
# |          0 | ezidapp_searchidentifier_resourcePublisher                       |
# |          0 | ezidapp_searchidentifier_resourceTitle                           |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx |
# +------------+------------------------------------------------------------------+
#
# Ordered by sum_time_wait:
#
# +------------+------------------------------------------------------------------+
# | count_star | index_name                                                       |
# +------------+------------------------------------------------------------------+
# | 8137471364 | identifier                                                       |
# | 1470097704 | ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx         |
# |   64647693 | ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx |
# |   60195608 | ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx |
# | 1694234344 | ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx |
# |   93001201 | ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx           |
# |     526415 | NULL                                                             |
# |    2066432 | PRIMARY                                                          |
# |   71055879 | ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx           |
# |  211448890 | ezidapp_searchidentifier_5e7b1936                                |
# |   23410277 | ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx      |
# |   14274173 | ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx      |
# |   30770472 | ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx           |
# |   59627193 | ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx           |
# |   84129679 | ezidapp_searchidentifier_365b2611                                |
# |   81640063 | ezidapp_searchidentifier_13bc2970                                |
# |   27213349 | ezidapp_searchidentifier_83a0eb3f                                |
# |    2549026 | ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx           |
# |   14193439 | ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx      |
# |    1600118 | ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx           |
# |    4652160 | ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx      |
# |   14880395 | ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx           |
# |   11497247 | ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx      |
# |   19388568 | ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx           |
# |    3779471 | ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx      |
# |    4298890 | ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx      |
# |    5411586 | ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx           |
# |    3023677 | ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx           |
# |    3001925 | ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx           |
# |    2991637 | ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx      |
# |     747300 | ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx      |
# |      86164 | ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx           |
# |       4718 | ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx |
# |       5492 | ezidapp_searchidentifier_owner_id_18a46334256a7530_idx           |
# |      35588 | ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx      |
# |          4 | ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx   |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx |
# |          0 | ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx      |
# |          0 | ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx      |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx |
# |          0 | ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx       |
# |          0 | ezidapp_searchidentifier_keywords                                |
# |          0 | ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx |
# |          0 | ezidapp_searchidentifier_resourcePublisher                       |
# |          0 | ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx      |
# |          0 | ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx |
# |          0 | ezidapp_searchidentifier_resourceCreator                         |
# |          0 | ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx           |
# |          0 | ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx           |
# |          0 | ezidapp_searchidentifier_resourceTitle                           |
# |          0 | ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx      |
# +------------+------------------------------------------------------------------+
# 51 rows in set (0.00 sec)
