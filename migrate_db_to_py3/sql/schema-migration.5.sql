use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

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