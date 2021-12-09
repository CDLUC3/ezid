/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# Drop indexes that may slow down operations on ezidapp_searchidentifier

# Drop foreign key constraints first, to enable dropping the associated indexes
alter table ezidapp_searchidentifier
drop foreign key `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id`,
drop foreign key `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id`,
drop foreign key `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id`,
drop foreign key `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id`
;

# Drop keys and indexes (all except for the id and identifier indexes)
alter table ezidapp_searchidentifier
drop index ezidapp_searchidentifie_publicsearchvisible_117042133b78a88e_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_1932465b0335635c_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_1e447c57e83c8d5d_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_2e067bd0a9494a38_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_47396846c619370f_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_47b0a294295f5ef5_idx,
drop index ezidapp_searchidentifie_publicsearchvisible_58de9f6f00b8058e_idx,
drop index ezidapp_searchidentifier_13bc2970,
drop index ezidapp_searchidentifier_365b2611,
drop index ezidapp_searchidentifier_5e7b1936,
drop index ezidapp_searchidentifier_83a0eb3f,
drop index ezidapp_searchidentifier_oaivisible_1d291a23fcff2ce2_idx,
drop index ezidapp_searchidentifier_owner_id_18a46334256a7530_idx,
drop index ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx,
drop index ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx,
drop index ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx,
drop index ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx,
drop index ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx,
drop index ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx,
drop index ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx,
drop index ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx,
drop index ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx,
drop index ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx,
drop index ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx,
drop index ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx,
drop index ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx,
drop index ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx,
drop index ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx,
drop index ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx,
drop index ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx,
drop index ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx,
drop index ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx,
drop index ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx,
drop index ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx,
drop index ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx,
drop index ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx,
drop index ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx,
drop index ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx,
drop index ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx,
drop index ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx,
drop index ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx,
drop index ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx,
drop index ezidapp_searchidentifier_publicsearchvisible_6807647c6d8cb52_idx,
drop index ezidapp_searchidentifier_searchabletarget_24d34538786996df_idx,
drop key ezidapp_searchidentifier_keywords,
drop key ezidapp_searchidentifier_resourcecreator,
drop key ezidapp_searchidentifier_resourcepublisher,
drop key ezidapp_searchidentifier_resourcetitle
;

# Translate from search to store FKs in ezidapp_searchidentifier
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

# Add JSON metadata columns
# Time on stg-py3, after upgrades, 2021-12-05: 20 min
alter table `ezidapp_searchidentifier`
add column `metadata` json null check (json_valid(`metadata`));

alter table `ezidapp_storeidentifier`
add column `metadata` json null check (json_valid(`metadata`));


# Add async queues

drop table if exists ezidapp_binderqueue;
drop table if exists ezidapp_crossrefqueue;
drop table if exists ezidapp_datacitequeue;
drop table if exists ezidapp_downloadqueue;
drop table if exists ezidapp_searchindexerqueue;
drop table if exists ezidapp_updatequeue;

create table `ezidapp_searchindexerqueue` (
    `seq` int not null auto_increment,
    `enqueueTime` int not null,
    `submitTime` int default null,
    `operation` varchar(1) not null,
    `status` varchar(1) not null,
    `message` longtext not null,
    `batchId` varchar(36) not null,
    `error` longtext not null,
    `errorIsPermanent` tinyint(1) not null,
    `refIdentifier_id` int not null,
    primary key (`seq`),
    key `ezidapp_searchindexe_refIdentifier_id_7b72d1a2_fk_ezidapp_r`(`refIdentifier_id`),
    key `ezidapp_searchindexerqueue_operation_577fd676`(`operation`),
    key `ezidapp_searchindexerqueue_status_9aeeb55e`(`status`)
    constraint `ezidapp_searchindexe_refIdentifier_id_7b72d1a2_fk_ezidapp_r` foreign key (`refIdentifier_id`) references `ezidapp_refidentifier`(`id`)
)
    engine = InnoDB
    default charset = utf8mb4
;

create table ezidapp_binderqueue like ezidapp_searchindexerqueue;
create table ezidapp_crossrefqueue like ezidapp_searchindexerqueue;
create table ezidapp_datacitequeue like ezidapp_searchindexerqueue;
create table ezidapp_downloadqueue like ezidapp_searchindexerqueue;
create table ezidapp_updatequeue like ezidapp_searchindexerqueue;



create table ezidapp_newsfeed (
    id integer auto_increment not null primary key,
    feed_id varchar(255) not null unique,
    published datetime(6) not null,
    title longtext not null,
    link varchar(200) not null
)
;

select * from ezidapp_newsfeed;



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



# Add constraints back, in order of importance

# !!! The optimal order has not been determined yet !!!

alter table ezidapp_searchidentifier
add constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_storeuser` (`id`),
add constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_storegroup` (`id`),
add constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_storeprofile` (`id`),
add constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_storedatacenter` (`id`)
;

# Crate fulltext indexes (one at a time)
# ERROR 1795 (HY000): InnoDB presently supports one FULLTEXT index creation at a time
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_keywords(keywords);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcecreator(resourcecreator);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcepublisher(resourcepublisher);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcetitle(resourcetitle);
select now();

alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_5e7b1936`(`owner_id`),
add key `ezidapp_searchidentifier_365b2611`(`ownergroup_id`),
add key `ezidapp_searchidentifier_13bc2970`(`datacenter_id`),
add key `ezidapp_searchidentifier_83a0eb3f`(`profile_id`),
add key `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx`(`owner_id`, `identifier`),
add key `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx`(`ownergroup_id`, `identifier`),
add key `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx`(`owner_id`, `createTime`),
add key `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx`(`owner_id`, `updateTime`),
add key `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx`(`owner_id`, `status`),
add key `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx`(`owner_id`, `exported`),
add key `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx`(`owner_id`, `crossrefStatus`),
add key `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx`(`owner_id`, `profile_id`),
add key `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx`(`owner_id`, `isTest`),
add key `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx`(`owner_id`, `searchablePublicationYear`),
add key `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx`(`owner_id`, `searchableResourceType`),
add key `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx`(`owner_id`, `hasMetadata`),
add key `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx`(`owner_id`, `hasIssues`),
add key `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx`(`owner_id`, `resourceCreatorPrefix`),
add key `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx`(`owner_id`, `resourceTitlePrefix`),
add key `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx`(`owner_id`, `resourcePublisherPrefix`),
add key `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx`(`ownergroup_id`, `createTime`),
add key `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx`(`ownergroup_id`, `updateTime`),
add key `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx`(`ownergroup_id`, `status`),
add key `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx`(`ownergroup_id`, `exported`),
add key `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx`(`ownergroup_id`, `crossrefStatus`),
add key `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx`(`ownergroup_id`, `profile_id`),
add key `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx`(`ownergroup_id`, `isTest`),
add key `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx`(`ownergroup_id`, `searchablePublicationYear`),
add key `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx`(`ownergroup_id`, `searchableResourceType`),
add key `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx`(`ownergroup_id`, `hasMetadata`),
add key `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx`(`ownergroup_id`, `hasIssues`),
add key `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx`(`ownergroup_id`, `resourceCreatorPrefix`),
add key `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx`(`ownergroup_id`, `resourceTitlePrefix`),
add key `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx`(`ownergroup_id`, `resourcePublisherPrefix`),
add key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx`(`publicSearchVisible`, `identifier`),
add key `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx`(`publicSearchVisible`, `createTime`),
add key `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx`(`publicSearchVisible`, `updateTime`),
add key `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx`(`publicSearchVisible`, `searchablePublicationYear`),
add key `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx`(`publicSearchVisible`, `searchableResourceType`),
add key `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx`(`publicSearchVisible`, `resourceCreatorPrefix`),
add key `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx`(`publicSearchVisible`, `resourceTitlePrefix`),
add key `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx`(`publicSearchVisible`, `resourcePublisherPrefix`),
add key `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx`(`searchableTarget`),
add key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx`(`oaiVisible`, `updateTime`)
;

alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourceTitle`(`resourceTitle`) ;
alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourceCreator`(`resourceCreator`) ;
alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourcePublisher`(`resourcePublisher`) ;
alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_keywords`(`keywords`) ;
