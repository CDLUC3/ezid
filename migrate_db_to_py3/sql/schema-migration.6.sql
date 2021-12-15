use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

# This is the final step to run before starting EZID.

# Add async queues

drop table if exists ezidapp_binderqueue;
drop table if exists ezidapp_crossrefqueue;
drop table if exists ezidapp_datacitequeue;
drop table if exists ezidapp_downloadqueue;
drop table if exists ezidapp_updatequeue;

drop table if exists ezidapp_searchindexerqueue;

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
    key `ezidapp_searchindexerqueue_status_9aeeb55e`(`status`),
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


drop table if exists ezidapp_newsfeed;

create table ezidapp_newsfeed (
    id integer auto_increment not null primary key,
    feed_id varchar(255) not null unique,
    published datetime(6) not null,
    title longtext not null,
    link varchar(200) not null
)
;

drop table if exists ezidapp_downloadqueue;

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
    charset = utf8mb4
;

# Crate fulltext indexes (must be done one at a time)
# These are required by EZID
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_keywords(keywords);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcecreator(resourcecreator);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcepublisher(resourcepublisher);
select now();
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcetitle(resourcetitle);
select now();

# 10 min
alter table ezidapp_searchidentifier
add constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_storeuser` (`id`),
add constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_storegroup` (`id`),
add constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_storeprofile` (`id`),
add constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_storedatacenter` (`id`)
;

# alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourceTitle`(`resourceTitle`) ;
# alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourceCreator`(`resourceCreator`) ;
# alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_resourcePublisher`(`resourcePublisher`) ;
# alter table ezidapp_searchidentifier add fulltext key `ezidapp_searchidentifier_keywords`(`keywords`) ;

# Add most used keys, using a batch query

# 1694234344 | ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx
# 1470014804 | ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx
#  211448890 | ezidapp_searchidentifier_5e7b1936
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx`(`publicSearchVisible`, `identifier`),
add key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx`(`oaiVisible`, `updateTime`),
add key `ezidapp_searchidentifier_5e7b1936`(`owner_id`)
;