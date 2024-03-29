/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

use ezid;

set @@autocommit = 0;
set unique_checks = 0;
set foreign_key_checks = 0;

show engine innodb status;
show table status;
show full processlist;
select version();

kill 50;

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

# Check for invalid foreign keys.

DROP PROCEDURE IF EXISTS ANALYZE_INVALID_FOREIGN_KEYS;
DELIMITER $$
CREATE
    PROCEDURE `ANALYZE_INVALID_FOREIGN_KEYS`(
        checked_database_name VARCHAR(64),
        checked_table_name VARCHAR(64),
        temporary_result_table ENUM('Y', 'N'))

    LANGUAGE SQL
    NOT DETERMINISTIC
    READS SQL DATA

    BEGIN
        DECLARE TABLE_SCHEMA_VAR VARCHAR(64);
        DECLARE TABLE_NAME_VAR VARCHAR(64);
        DECLARE COLUMN_NAME_VAR VARCHAR(64);
        DECLARE CONSTRAINT_NAME_VAR VARCHAR(64);
        DECLARE REFERENCED_TABLE_SCHEMA_VAR VARCHAR(64);
        DECLARE REFERENCED_TABLE_NAME_VAR VARCHAR(64);
        DECLARE REFERENCED_COLUMN_NAME_VAR VARCHAR(64);
        DECLARE KEYS_SQL_VAR VARCHAR(1024);

        DECLARE done INT DEFAULT 0;

        DECLARE foreign_key_cursor CURSOR FOR
            SELECT
                `TABLE_SCHEMA`,
                `TABLE_NAME`,
                `COLUMN_NAME`,
                `CONSTRAINT_NAME`,
                `REFERENCED_TABLE_SCHEMA`,
                `REFERENCED_TABLE_NAME`,
                `REFERENCED_COLUMN_NAME`
            FROM
                information_schema.KEY_COLUMN_USAGE
            WHERE
                `CONSTRAINT_SCHEMA` LIKE checked_database_name AND
                `TABLE_NAME` LIKE checked_table_name AND
                `REFERENCED_TABLE_SCHEMA` IS NOT NULL;

        DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

        IF temporary_result_table = 'N' THEN
            DROP TEMPORARY TABLE IF EXISTS INVALID_FOREIGN_KEYS;
            DROP TABLE IF EXISTS INVALID_FOREIGN_KEYS;

            CREATE TABLE INVALID_FOREIGN_KEYS(
                `TABLE_SCHEMA` VARCHAR(64),
                `TABLE_NAME` VARCHAR(64),
                `COLUMN_NAME` VARCHAR(64),
                `CONSTRAINT_NAME` VARCHAR(64),
                `REFERENCED_TABLE_SCHEMA` VARCHAR(64),
                `REFERENCED_TABLE_NAME` VARCHAR(64),
                `REFERENCED_COLUMN_NAME` VARCHAR(64),
                `INVALID_KEY_COUNT` INT,
                `INVALID_KEY_SQL` VARCHAR(1024)
            );
        ELSEIF temporary_result_table = 'Y' THEN
            DROP TEMPORARY TABLE IF EXISTS INVALID_FOREIGN_KEYS;
            DROP TABLE IF EXISTS INVALID_FOREIGN_KEYS;

            CREATE TEMPORARY TABLE INVALID_FOREIGN_KEYS(
                `TABLE_SCHEMA` VARCHAR(64),
                `TABLE_NAME` VARCHAR(64),
                `COLUMN_NAME` VARCHAR(64),
                `CONSTRAINT_NAME` VARCHAR(64),
                `REFERENCED_TABLE_SCHEMA` VARCHAR(64),
                `REFERENCED_TABLE_NAME` VARCHAR(64),
                `REFERENCED_COLUMN_NAME` VARCHAR(64),
                `INVALID_KEY_COUNT` INT,
                `INVALID_KEY_SQL` VARCHAR(1024)
            );
        END IF;


        OPEN foreign_key_cursor;
        foreign_key_cursor_loop: LOOP
            FETCH foreign_key_cursor INTO
            TABLE_SCHEMA_VAR,
            TABLE_NAME_VAR,
            COLUMN_NAME_VAR,
            CONSTRAINT_NAME_VAR,
            REFERENCED_TABLE_SCHEMA_VAR,
            REFERENCED_TABLE_NAME_VAR,
            REFERENCED_COLUMN_NAME_VAR;
            IF done THEN
                LEAVE foreign_key_cursor_loop;
            END IF;


            SET @from_part = CONCAT('FROM ', '`', TABLE_SCHEMA_VAR, '`.`', TABLE_NAME_VAR, '`', ' AS REFERRING ',
                 'LEFT JOIN `', REFERENCED_TABLE_SCHEMA_VAR, '`.`', REFERENCED_TABLE_NAME_VAR, '`', ' AS REFERRED ',
                 'ON (REFERRING', '.`', COLUMN_NAME_VAR, '`', ' = ', 'REFERRED', '.`', REFERENCED_COLUMN_NAME_VAR, '`', ') ',
                 'WHERE REFERRING', '.`', COLUMN_NAME_VAR, '`', ' IS NOT NULL ',
                 'AND REFERRED', '.`', REFERENCED_COLUMN_NAME_VAR, '`', ' IS NULL');
            SET @full_query = CONCAT('SELECT COUNT(*) ', @from_part, ' INTO @invalid_key_count;');
            PREPARE stmt FROM @full_query;

            EXECUTE stmt;
            IF @invalid_key_count > 0 THEN
                INSERT INTO
                    INVALID_FOREIGN_KEYS
                SET
                    `TABLE_SCHEMA` = TABLE_SCHEMA_VAR,
                    `TABLE_NAME` = TABLE_NAME_VAR,
                    `COLUMN_NAME` = COLUMN_NAME_VAR,
                    `CONSTRAINT_NAME` = CONSTRAINT_NAME_VAR,
                    `REFERENCED_TABLE_SCHEMA` = REFERENCED_TABLE_SCHEMA_VAR,
                    `REFERENCED_TABLE_NAME` = REFERENCED_TABLE_NAME_VAR,
                    `REFERENCED_COLUMN_NAME` = REFERENCED_COLUMN_NAME_VAR,
                    `INVALID_KEY_COUNT` = @invalid_key_count,
                    `INVALID_KEY_SQL` = CONCAT('SELECT ',
                        'REFERRING.', '`', COLUMN_NAME_VAR, '` ', 'AS "Invalid: ', COLUMN_NAME_VAR, '", ',
                        'REFERRING.* ',
                        @from_part, ';');
            END IF;
            DEALLOCATE PREPARE stmt;

        END LOOP foreign_key_cursor_loop;
    END$$

DELIMITER ;

CALL ANALYZE_INVALID_FOREIGN_KEYS('%', '%', 'Y');
DROP PROCEDURE IF EXISTS ANALYZE_INVALID_FOREIGN_KEYS;

SELECT * FROM INVALID_FOREIGN_KEYS;


######


select
    ( select count(*) from ezidapp_searchidentifier) as search,
    ( select count(*) from ezidapp_storeidentifier) as store,
    ( select count(*) from ezidapp_searchidentifier where metadata is not null) as metadata_not_null
;

select publicsearchvisible, count(*) from ezidapp_searchidentifier es group by es.publicsearchvisible;

show create table ezidapp_searchidentifier;

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


# Test the keywords fulltext index
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


update ezidapp_searchidentifier si
    join ezidapp_searchuser searchuser on searchuser.id = si.owner_id
    join ezidapp_storeuser storeuser on storeuser.pid = searchuser.pid
    left join ezidapp_searchgroup searchgroup on searchgroup.id = si.ownergroup_id
    left join ezidapp_storegroup storegroup on storegroup.pid = searchgroup.pid
    left join ezidapp_searchprofile searchprofile on searchprofile.id = si.profile_id
    left join ezidapp_storeprofile storeprofile on storeprofile.label = searchprofile.label
    left join ezidapp_searchdatacenter searchdatacenter on searchdatacenter.id = si.datacenter_id
    left join ezidapp_storedatacenter storedatacenter on storedatacenter.symbol = searchdatacenter.symbol
set si.owner_id      = storeuser.id,
    si.ownergroup_id = storegroup.id,
    si.profile_id    = storeprofile.id,
    si.datacenter_id = storedatacenter.id
where true
;



# alter table ezidapp_searchuser
# drop foreign key ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id,
# drop foreign key ezidapp_sear_realm_id_3d437af11e1add07_fk_ezidapp_searchrealm_id
# ;
#
# alter table ezidapp_searchuser
# drop key ezidapp_sear_group_id_488efb1f64647b87_fk_ezidapp_searchgroup_id
# ;

# Check FKs

select count(*) from ezidapp_identifier;
select * from ezidapp_user_shoulders order by user_id;
select * from ezidapp_user order by id;

select count(*) from ezidapp_user_shoulders;
select count(*) from ezidapp_user_shoulders where user_id not in (select id from ezidapp_user);

SELECT (`ezidapp_user_shoulders`.`user_id`) AS `_prefetch_related_val_user_id`,
 `ezidapp_shoulder`.`id`,
 `ezidapp_shoulder`.`prefix`,
 `ezidapp_shoulder`.`type`,
 `ezidapp_shoulder`.`name`,
 `ezidapp_shoulder`.`minter`,
 `ezidapp_shoulder`.`datacenter_id`,
 `ezidapp_shoulder`.`crossrefEnabled`,
 `ezidapp_shoulder`.`isTest`,
 `ezidapp_shoulder`.`shoulder_type_id`,
 `ezidapp_shoulder`.`registration_agency_id`,
 `ezidapp_shoulder`.`prefix_shares_datacenter`,
 `ezidapp_shoulder`.`manager`,
 `ezidapp_shoulder`.`active`,
 `ezidapp_shoulder`.`redirect`,
 `ezidapp_shoulder`.`date`,
 `ezidapp_shoulder`.`isSupershoulder`
  FROM `ezidapp_shoulder`
 INNER JOIN `ezidapp_user_shoulders`
 ON (`ezidapp_shoulder`.`id` = `ezidapp_user_shoulders`.`shoulder_id`)
 WHERE `ezidapp_user_shoulders`.`user_id` IN (1)
 ;

select * from auth_group_permissions;
select * from auth_user_groups;
select * from auth_group;
select * from auth_user_user_permissions;
select * from auth_permission;
select * from django_admin_log;
select * from django_content_type;
select * from auth_user;
select * from django_migrations;
select * from django_session;

update ezidapp_user set realm_id = 1;
update ezidapp_group set realm_id = 1;
delete from ezidapp_realm where id <> 1;
update ezidapp_realm set name = 'CDL';

select * from auth_permission ap;

update ezidapp_searchidentifier set
    owner_id = case when 1 then 1 when 2 then 2 when 10 then 75 when 13 then 243 when 14 then 248 when 21 then 186 when 26 then 223 when 28 then 65 when 30 then 240 when 31 then 202 when 39 then 66 when 40 then 87 when 48 then 184 when 52 then 152 when 53 then 242 when 69 then 247 when 75 then 44 when 80 then 182 when 89 then 111 when 93 then 233 when 96 then 212 when 99 then 230 when 101 then 185 when 102 then 57 when 104 then 110 when 108 then 214 when 111 then 163 when 114 then 207 when 116 then 228 when 117 then 275 when 118 then 60 when 119 then 208 when 120 then 213 when 123 then 198 when 124 then 209 when 126 then 179 when 130 then 22 when 131 then 59 when 135 then 204 when 136 then 289 when 137 then 39 when 139 then 134 when 140 then 172 when 145 then 180 when 152 then 26 when 159 then 9 when 160 then 234 when 166 then 238 when 171 then 15 when 173 then 220 when 175 then 201 when 180 then 244 when 186 then 237 when 187 then 139 when 188 then 210 when 191 then 211 when 192 then 232 when 193 then 130 when 195 then 245 when 199 then 226 when 204 then 56 when 206 then 100 when 207 then 227 when 210 then 23 when 211 then 268 when 213 then 49 when 214 then 235 when 216 then 98 when 219 then 181 when 222 then 195 when 225 then 231 when 227 then 216 when 228 then 52 when 229 then 25 when 230 then 124 when 232 then 217 when 235 then 170 when 236 then 219 when 237 then 241 when 239 then 67 when 241 then 206 when 244 then 225 when 245 then 196 when 246 then 205 when 249 then 99 when 252 then 70 when 261 then 183 when 268 then 108 when 269 then 203 when 271 then 246 when 272 then 229 when 276 then 109 when 277 then 10 when 279 then 292 when 281 then 105 when 282 then 11 when 284 then 222 when 285 then 221 when 286 then 224 when 287 then 200 when 290 then 107 when 292 then 290 when 297 then 295 when 298 then 296 when 300 then 298 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 when 311 then 309 when 316 then 314 when 320 then 318 when 323 then 321 when 324 then 322 when 326 then 324 when 327 then 325 when 328 then 326 when 333 then 331 when 334 then 332 when 337 then 335 when 338 then 336 when 340 then 338 when 342 then 340 when 344 then 342 when 345 then 343 when 349 then 347 when 350 then 348 when 351 then 349 when 354 then 352 when 358 then 356 when 359 then 357 when 361 then 359 when 362 then 360 when 363 then 361 when 365 then 363 when 366 then 364 when 371 then 369 when 372 then 370 when 375 then 373 when 378 then 376 when 379 then 377 when 386 then 384 when 387 then 385 when 388 then 386 when 389 then 387 when 390 then 388 when 391 then 389 when 392 then 390 when 393 then 391 when 394 then 392 when 395 then 393 when 396 then 394 when 397 then 395 when 398 then 396 when 399 then 397 when 400 then 398 when 401 then 399 when 402 then 400 when 403 then 401 when 404 then 402 when 406 then 404 when 407 then 405 when 408 then 406 when 409 then 407 when 410 then 408 when 411 then 409 when 415 then 413 when 416 then 414 when 417 then 415 when 418 then 416 when 419 then 417 when 420 then 418 when 422 then 420 when 423 then 421 when 424 then 422 when 426 then 424 when 427 then 425 when 428 then 426 when 429 then 427 when 430 then 428 when 431 then 429 when 432 then 430 when 433 then 431 when 434 then 432 when 435 then 433 when 436 then 434 when 437 then 435 when 438 then 437 when 439 then 438 when 440 then 439 when 441 then 440 when 443 then 442 when 444 then 443 when 445 then 444 when 446 then 445 when 447 then 446 when 448 then 447 when 449 then 448 when 450 then 449 when 451 then 450 when 452 then 451 when 453 then 452 when 454 then 453 when 455 then 454 when 456 then 455 when 457 then 456 when 458 then 457 when 459 then 458 when 460 then 459 when 461 then 460 when 462 then 461 when 463 then 462 when 464 then 463 when 465 then 464 when 466 then 465 when 468 then 467 when 469 then 468 when 470 then 469 when 471 then 470 when 472 then 471 when 473 then 472 when 474 then 473 when 475 then 474 when 476 then 475 when 477 then 476 when 478 then 477 end,
    ownergroup_id = case when 1 then 1 when 2 then 2 when 3 then 223 when 7 then 28 when 10 then 21 when 13 then 263 when 22 then 196 when 27 then 84 when 35 then 172 when 38 then 23 when 39 then 145 when 50 then 186 when 53 then 57 when 55 then 121 when 75 then 112 when 94 then 202 when 108 then 247 when 110 then 187 when 117 then 190 when 125 then 203 when 137 then 14 when 147 then 199 when 153 then 51 when 158 then 106 when 161 then 171 when 176 then 159 when 177 then 22 when 185 then 47 when 200 then 224 when 206 then 116 when 211 then 242 when 215 then 192 when 220 then 92 when 235 then 39 when 251 then 10 when 265 then 264 when 275 then 273 when 283 then 281 when 288 then 286 when 292 then 290 when 296 then 294 when 297 then 295 when 299 then 297 when 301 then 299 when 303 then 301 when 304 then 302 when 305 then 303 when 306 then 304 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 end,
    profile_id = case when 1 then 1 when 2 then 3 when 3 then 2 when 4 then 5 when 5 then 4 when 8 then 8 when 9 then 9 when 11 then 11 when 12 then 12 when 13 then 13 end,
    datacenter_id = case when 1 then 268 when 7 then 1 when 9 then 207 when 15 then 9 when 24 then 181 when 27 then 205 when 29 then 158 when 47 then 182 when 56 then 208 when 97 then 274 when 111 then 271 when 124 then 275 when 139 then 273 when 174 then 270 when 180 then 184 when 196 then 269 when 200 then 272 when 209 then 276 when 223 then 266 when 224 then 267 end
where id < 10000
;

start transaction;

update ezidapp_searchidentifier set
    ownergroup_id = ( case
        when ownergroup_id = 7 then 28
        when ownergroup_id = 38 then 23
        when ownergroup_id = 110 then 187
        when ownergroup_id = 177 then 190
        when ownergroup_id = 200 then 224
        else 1000
    end )
where id < 10000
;

select count(*), ownergroup_id
from ezidapp_searchidentifier
where id < 10000
group by ownergroup_id
;

rollback;

select ownergroup_id
from ezidapp_searchidentifier
where id < 10000
;

select case
    when ownergroup_id = 177 then 190
    when ownergroup_id = 7 then 28
    when ownergroup_id = 38 then 23
    when ownergroup_id = 110 then 187
    when ownergroup_id = 200 then 224
    else 1000
end
from ezidapp_searchidentifier
where id < 10000
;

select count(*) from ezidapp_searchidentifier where ownergroup_id not in (
    1,2,3,7,10,13,22,27,35,38,39,50,53,55,75,94,108,110,117,125,137,147,153,158,161,176,177,185,200,206,211,215,220,235,251,265,275,283,288,292,296,297,299,301,303,304,305,306,307,308,309,310
)
;

SELECT COUNT(*)
FROM `ezidapp_searchidentifier`
INNER JOIN `ezidapp_group`  ON (`ezidapp_searchidentifier`.`ownergroup_id` = `ezidapp_group`.`id`)
WHERE `ezidapp_group`.`groupname` = 'admin'
;

select * from ezidapp_group
where `ezidapp_group`.`groupname` = 'admin'
;

select count(*), ownergroup_id
from ezidapp_searchidentifier
group by ownergroup_id
;

select count(*), owner_id
from ezidapp_searchidentifier
group by owner_id
;

where ownergroup_id = 1;

update ezidapp_group set organizationname = 'EZID superuser' where groupname = 'admin';

select * from ezidapp_group;

INSERT INTO `ezidapp_storegroup`
VALUES (1,'ark:/99166/p9g44hq02','admin','EZID superuser','','http://ezid.cdlib.org/','(:unap)',0,0,'',1,'')
;

select * from ezidapp_group eg;
delete from ezidapp_group where id = 309;

select * from ezidapp_identifier ei where ei.ownergroup_id = 309;
delete from ezidapp_identifier where ownergroup_id = 309;

select * from ezidapp_shoulder es where group_id = 309;

SELECT *
FROM `ezidapp_searchidentifier`
INNER JOIN `ezidapp_user`
ON (`ezidapp_searchidentifier`.`owner_id` = `ezidapp_user`.`id`)
WHERE (`ezidapp_user`.`username` = 'all')
;

LEFT OUTER JOIN `ezidapp_group` ON (`ezidapp_searchidentifier`.`ownergroup_id` = `ezidapp_group`.`id`)
WHERE (`ezidapp_user`.`username` = 'all'
AND `ezidapp_searchidentifier`.`identifier` LIKE BINARY 'ark:/99166/p96m3392n%')
ORDER BY `ezidapp_searchidentifier`.`updateTime` DESC LIMIT 10;


select * from ezidapp_searchidentifier where identifier = 'ark:/99166/p96m3392n';

show create table ezidapp_searchidentifier;
CREATE TABLE `ezidapp_searchidentifier` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `identifier` varchar(255) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  `createTime` int(11) NOT NULL,
  `updateTime` int(11) NOT NULL,
  `status` varchar(1) NOT NULL,
  `unavailableReason` longtext CHARACTER SET utf8mb4 NOT NULL,
  `exported` tinyint(1) NOT NULL,
  `crossrefStatus` varchar(1) NOT NULL,
  `crossrefMessage` longtext CHARACTER SET utf8mb4 NOT NULL,
  `target` varchar(2000) NOT NULL,
  `cm` longblob NOT NULL,
  `agentRole` varchar(1) NOT NULL,
  `isTest` tinyint(1) NOT NULL,
  `owner_id` int(11) NOT NULL,
  `ownergroup_id` int(11) NOT NULL,
  `datacenter_id` int(11) DEFAULT NULL,
  `profile_id` int(11) NOT NULL,
  `searchableTarget` varchar(255) NOT NULL,
  `resourceCreator` longtext CHARACTER SET utf8mb4 NOT NULL,
  `resourceTitle` longtext CHARACTER SET utf8mb4 NOT NULL,
  `resourcePublisher` longtext CHARACTER SET utf8mb4 NOT NULL,
  `resourcePublicationDate` longtext CHARACTER SET utf8mb4 NOT NULL,
  `searchablePublicationYear` int(11) DEFAULT NULL,
  `resourceType` longtext CHARACTER SET utf8mb4 NOT NULL,
  `searchableResourceType` varchar(2) NOT NULL,
  `keywords` longtext CHARACTER SET utf8mb4 NOT NULL,
  `resourceCreatorPrefix` varchar(50) CHARACTER SET utf8mb4 NOT NULL,
  `resourceTitlePrefix` varchar(50) CHARACTER SET utf8mb4 NOT NULL,
  `resourcePublisherPrefix` varchar(50) CHARACTER SET utf8mb4 NOT NULL,
  `hasMetadata` tinyint(1) NOT NULL,
  `publicSearchVisible` tinyint(1) NOT NULL,
  `oaiVisible` tinyint(1) NOT NULL,
  `hasIssues` tinyint(1) NOT NULL,
  `linkIsBroken` tinyint(1) NOT NULL,
  `metadata` json DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `identifier` (`identifier`),
  KEY `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` (`owner_id`),
  KEY `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` (`ownergroup_id`),
  KEY `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` (`profile_id`),
  KEY `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` (`datacenter_id`),
  FULLTEXT KEY `ezidapp_searchidentifier_keywords` (`keywords`),
  FULLTEXT KEY `ezidapp_searchidentifier_resourcecreator` (`resourceCreator`),
  FULLTEXT KEY `ezidapp_searchidentifier_resourcepublisher` (`resourcePublisher`),
  FULLTEXT KEY `ezidapp_searchidentifier_resourcetitle` (`resourceTitle`),
  CONSTRAINT `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` FOREIGN KEY (`datacenter_id`) REFERENCES `ezidapp_storedatacenter` (`id`),
  CONSTRAINT `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` FOREIGN KEY (`profile_id`) REFERENCES `ezidapp_storeprofile` (`id`),
  CONSTRAINT `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` FOREIGN KEY (`ownergroup_id`) REFERENCES `ezidapp_storegroup` (`id`),
  CONSTRAINT `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` FOREIGN KEY (`owner_id`) REFERENCES `ezidapp_storeuser` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=127562335 DEFAULT CHARSET=utf8 STATS_SAMPLE_PAGES=2000

select count(*) from ezidapp_storeidentifier es;

select * from ezidapp_shoulder;

SELECT (`ezidapp_user_shoulders`.`user_id`) AS `_prefetch_related_val_user_id`, `ezidapp_shoulder`.`id`, `ezidapp_shoulder`.`prefix`, `ezidapp_shoulder`.`type`, `ezidapp_shoulder`.`name`, `ezidapp_shoulder`.`minter`, `ezidapp_shoulder`.`datacenter_id`, `ezidapp_shoulder`.`crossrefEnabled`, `ezidapp_shoulder`.`isTest`, `ezidapp_shoulder`.`shoulder_type_id`, `ezidapp_shoulder`.`registration_agency_id`, `ezidapp_shoulder`.`prefix_shares_datacenter`, `ezidapp_shoulder`.`manager`, `ezidapp_shoulder`.`active`, `ezidapp_shoulder`.`redirect`, `ezidapp_shoulder`.`date`, `ezidapp_shoulder`.`isSupershoulder` FROM `ezidapp_shoulder` INNER JOIN `ezidapp_user_shoulders` ON (`ezidapp_shoulder`.`id` = `ezidapp_user_shoulders`.`shoulder_id`) WHERE `ezidapp_user_shoulders`.`user_id` IN (1);
SELECT (`ezidapp_user_shoulders`.`user_id`) AS `_prefetch_related_val_user_id`, `ezidapp_shoulder`.`id`, `ezidapp_shoulder`.`prefix`, `ezidapp_shoulder`.`type`, `ezidapp_shoulder`.`name`, `ezidapp_shoulder`.`minter`, `ezidapp_shoulder`.`datacenter_id`, `ezidapp_shoulder`.`crossrefEnabled`, `ezidapp_shoulder`.`isTest`, `ezidapp_shoulder`.`shoulder_type_id`, `ezidapp_shoulder`.`registration_agency_id`, `ezidapp_shoulder`.`prefix_shares_datacenter`, `ezidapp_shoulder`.`manager`, `ezidapp_shoulder`.`active`, `ezidapp_shoulder`.`redirect`, `ezidapp_shoulder`.`date`, `ezidapp_shoulder`.`isSupershoulder` FROM `ezidapp_shoulder` INNER JOIN `ezidapp_user_shoulders` ON (`ezidapp_shoulder`.`id` = `ezidapp_user_shoulders`.`shoulder_id`)
WHERE `ezidapp_user_shoulders`.`user_id` IN (1);


SELECT `ezidapp_user`.`id`, `ezidapp_user`.`pid`, `ezidapp_user`.`username`, `ezidapp_user`.`group_id`, `ezidapp_user`.`realm_id`, `ezidapp_user`.`displayName`, `ezidapp_user`.`accountEmail`, `ezidapp_user`.`primaryContactName`, `ezidapp_user`.`primaryContactEmail`, `ezidapp_user`.`primaryContactPhone`, `ezidapp_user`.`secondaryContactName`, `ezidapp_user`.`secondaryContactEmail`, `ezidapp_user`.`secondaryContactPhone`, `ezidapp_user`.`inheritGroupShoulders`, `ezidapp_user`.`crossrefEnabled`, `ezidapp_user`.`crossrefEmail`, `ezidapp_user`.`isGroupAdministrator`, `ezidapp_user`.`isRealmAdministrator`, `ezidapp_user`.`isSuperuser`, `ezidapp_user`.`loginEnabled`, `ezidapp_user`.`password`, `ezidapp_user`.`notes`, `ezidapp_group`.`id`, `ezidapp_group`.`pid`, `ezidapp_group`.`groupname`, `ezidapp_group`.`realm_id`, `ezidapp_group`.`organizationName`, `ezidapp_group`.`organizationAcronym`, `ezidapp_group`.`organizationUrl`, `ezidapp_group`.`organizationStreetAddress`, `ezidapp_group`.`accountType`, `ezidapp_group`.`agreementOnFile`, `ezidapp_group`.`crossrefEnabled`, `ezidapp_group`.`notes`, `ezidapp_realm`.`id`, `ezidapp_realm`.`name` FROM `ezidapp_user` INNER JOIN `ezidapp_group` ON (`ezidapp_user`.`group_id` = `ezidapp_group`.`id`) INNER JOIN `ezidapp_realm` ON (`ezidapp_user`.`realm_id` = `ezidapp_realm`.`id`) WHERE `ezidapp_user`.`id` = 1 LIMIT 21;

SELECT `ezidapp_user`.`id`, `ezidapp_user`.`pid`, `ezidapp_user`.`username`, `ezidapp_user`.`group_id`, `ezidapp_user`.`realm_id`, `ezidapp_user`.`displayName`, `ezidapp_user`.`accountEmail`, `ezidapp_user`.`primaryContactName`, `ezidapp_user`.`primaryContactEmail`, `ezidapp_user`.`primaryContactPhone`, `ezidapp_user`.`secondaryContactName`, `ezidapp_user`.`secondaryContactEmail`, `ezidapp_user`.`secondaryContactPhone`, `ezidapp_user`.`inheritGroupShoulders`, `ezidapp_user`.`crossrefEnabled`, `ezidapp_user`.`crossrefEmail`, `ezidapp_user`.`isGroupAdministrator`, `ezidapp_user`.`isRealmAdministrator`, `ezidapp_user`.`isSuperuser`, `ezidapp_user`.`loginEnabled`, `ezidapp_user`.`password`, `ezidapp_user`.`notes`, `ezidapp_group`.`id`, `ezidapp_group`.`pid`, `ezidapp_group`.`groupname`, `ezidapp_group`.`realm_id`, `ezidapp_group`.`organizationName`, `ezidapp_group`.`organizationAcronym`, `ezidapp_group`.`organizationUrl`, `ezidapp_group`.`organizationStreetAddress`, `ezidapp_group`.`accountType`, `ezidapp_group`.`agreementOnFile`, `ezidapp_group`.`crossrefEnabled`, `ezidapp_group`.`notes`, `ezidapp_realm`.`id`, `ezidapp_realm`.`name` FROM `ezidapp_user` INNER JOIN `ezidapp_group` ON (`ezidapp_user`.`group_id` = `ezidapp_group`.`id`) INNER JOIN `ezidapp_realm` ON (`ezidapp_user`.`realm_id` = `ezidapp_realm`.`id`) WHERE `ezidapp_user`.`id` = 1 LIMIT 21;


SELECT `ezidapp_user`.`id`, `ezidapp_user`.`pid`, `ezidapp_user`.`username`, `ezidapp_user`.`group_id`, `ezidapp_user`.`realm_id`, `ezidapp_user`.`displayName`, `ezidapp_user`.`accountEmail`, `ezidapp_user`.`primaryContactName`, `ezidapp_user`.`primaryContactEmail`, `ezidapp_user`.`primaryContactPhone`, `ezidapp_user`.`secondaryContactName`, `ezidapp_user`.`secondaryContactEmail`, `ezidapp_user`.`secondaryContactPhone`, `ezidapp_user`.`inheritGroupShoulders`, `ezidapp_user`.`crossrefEnabled`, `ezidapp_user`.`crossrefEmail`, `ezidapp_user`.`isGroupAdministrator`, `ezidapp_user`.`isRealmAdministrator`, `ezidapp_user`.`isSuperuser`, `ezidapp_user`.`loginEnabled`, `ezidapp_user`.`password`, `ezidapp_user`.`notes`, `ezidapp_group`.`id`, `ezidapp_group`.`pid`, `ezidapp_group`.`groupname`, `ezidapp_group`.`realm_id`, `ezidapp_group`.`organizationName`, `ezidapp_group`.`organizationAcronym`, `ezidapp_group`.`organizationUrl`, `ezidapp_group`.`organizationStreetAddress`, `ezidapp_group`.`accountType`, `ezidapp_group`.`agreementOnFile`, `ezidapp_group`.`crossrefEnabled`, `ezidapp_group`.`notes`, `ezidapp_realm`.`id`, `ezidapp_realm`.`name` FROM `ezidapp_user` INNER JOIN `ezidapp_group` ON (`ezidapp_user`.`group_id` = `ezidapp_group`.`id`) INNER JOIN `ezidapp_realm` ON (`ezidapp_user`.`realm_id` = `ezidapp_realm`.`id`) WHERE `ezidapp_user`.`id` = 1 LIMIT 21; args=(1,)
SELECT `ezidapp_storeuser`.`id`, `ezidapp_storeuser`.`pid`, `ezidapp_storeuser`.`username`, `ezidapp_storeuser`.`group_id`, `ezidapp_storeuser`.`realm_id`, `ezidapp_storeuser`.`displayName`, `ezidapp_storeuser`.`accountEmail`, `ezidapp_storeuser`.`primaryContactName`, `ezidapp_storeuser`.`primaryContactEmail`, `ezidapp_storeuser`.`primaryContactPhone`, `ezidapp_storeuser`.`secondaryContactName`, `ezidapp_storeuser`.`secondaryContactEmail`, `ezidapp_storeuser`.`secondaryContactPhone`, `ezidapp_storeuser`.`inheritGroupShoulders`, `ezidapp_storeuser`.`crossrefEnabled`, `ezidapp_storeuser`.`crossrefEmail`, `ezidapp_storeuser`.`isGroupAdministrator`, `ezidapp_storeuser`.`isRealmAdministrator`, `ezidapp_storeuser`.`isSuperuser`, `ezidapp_storeuser`.`loginEnabled`, `ezidapp_storeuser`.`password`, `ezidapp_storeuser`.`notes`, `ezidapp_storegroup`.`id`, `ezidapp_storegroup`.`pid`, `ezidapp_storegroup`.`groupname`, `ezidapp_storegroup`.`realm_id`, `ezidapp_storegroup`.`organizationName`, `ezidapp_storegroup`.`organizationAcronym`, `ezidapp_storegroup`.`organizationUrl`, `ezidapp_storegroup`.`organizationStreetAddress`, `ezidapp_storegroup`.`accountType`, `ezidapp_storegroup`.`agreementOnFile`, `ezidapp_storegroup`.`crossrefEnabled`, `ezidapp_storegroup`.`notes`, `ezidapp_storerealm`.`id`, `ezidapp_storerealm`.`name` FROM `ezidapp_storeuser` INNER JOIN `ezidapp_storegroup` ON (`ezidapp_storeuser`.`group_id` = `ezidapp_storegroup`.`id`) INNER JOIN `ezidapp_storerealm` ON (`ezidapp_storeuser`.`realm_id` = `ezidapp_storerealm`.`id`) WHERE `ezidapp_storeuser`.`id` = 1 LIMIT 21;

# admin Group: EZID superuser

select * from ezidapp_group;


SELECT `ezidapp_user`.`id`, `ezidapp_user`.`pid`, `ezidapp_user`.`username`, `ezidapp_user`.`group_id`, `ezidapp_user`.`realm_id`, `ezidapp_user`.`displayName`, `ezidapp_user`.`accountEmail`, `ezidapp_user`.`primaryContactName`, `ezidapp_user`.`primaryContactEmail`, `ezidapp_user`.`primaryContactPhone`, `ezidapp_user`.`secondaryContactName`, `ezidapp_user`.`secondaryContactEmail`, `ezidapp_user`.`secondaryContactPhone`, `ezidapp_user`.`inheritGroupShoulders`, `ezidapp_user`.`crossrefEnabled`, `ezidapp_user`.`crossrefEmail`, `ezidapp_user`.`isGroupAdministrator`, `ezidapp_user`.`isRealmAdministrator`, `ezidapp_user`.`isSuperuser`, `ezidapp_user`.`loginEnabled`, `ezidapp_user`.`password`, `ezidapp_user`.`notes`, `ezidapp_group`.`id`, `ezidapp_group`.`pid`, `ezidapp_group`.`groupname`, `ezidapp_group`.`realm_id`, `ezidapp_group`.`organizationName`, `ezidapp_group`.`organizationAcronym`, `ezidapp_group`.`organizationUrl`, `ezidapp_group`.`organizationStreetAddress`, `ezidapp_group`.`accountType`, `ezidapp_group`.`agreementOnFile`, `ezidapp_group`.`crossrefEnabled`, `ezidapp_group`.`notes`, `ezidapp_realm`.`id`, `ezidapp_realm`.`name` FROM `ezidapp_user` INNER JOIN `ezidapp_group` ON (`ezidapp_user`.`group_id` = `ezidapp_group`.`id`) INNER JOIN `ezidapp_realm` ON (`ezidapp_user`.`realm_id` = `ezidapp_realm`.`id`) WHERE `ezidapp_user`.`id` = 1 LIMIT 21;
SELECT (`ezidapp_user_shoulders`.`user_id`) AS `_prefetch_related_val_user_id`, `ezidapp_shoulder`.`id`, `ezidapp_shoulder`.`prefix`, `ezidapp_shoulder`.`type`, `ezidapp_shoulder`.`name`, `ezidapp_shoulder`.`minter`, `ezidapp_shoulder`.`datacenter_id`, `ezidapp_shoulder`.`crossrefEnabled`, `ezidapp_shoulder`.`isTest`, `ezidapp_shoulder`.`shoulder_type_id`, `ezidapp_shoulder`.`registration_agency_id`, `ezidapp_shoulder`.`prefix_shares_datacenter`, `ezidapp_shoulder`.`manager`, `ezidapp_shoulder`.`active`, `ezidapp_shoulder`.`redirect`, `ezidapp_shoulder`.`date`, `ezidapp_shoulder`.`isSupershoulder` FROM `ezidapp_shoulder` INNER JOIN `ezidapp_user_shoulders` ON (`ezidapp_shoulder`.`id` = `ezidapp_user_shoulders`.`shoulder_id`) WHERE `ezidapp_user_shoulders`.`user_id` IN (1);
SELECT (`ezidapp_user_shoulders`.`user_id`) AS `_prefetch_related_val_user_id`, `ezidapp_shoulder`.`id`, `ezidapp_shoulder`.`prefix`, `ezidapp_shoulder`.`type`, `ezidapp_shoulder`.`name`, `ezidapp_shoulder`.`minter`, `ezidapp_shoulder`.`datacenter_id`, `ezidapp_shoulder`.`crossrefEnabled`, `ezidapp_shoulder`.`isTest`, `ezidapp_shoulder`.`shoulder_type_id`, `ezidapp_shoulder`.`registration_agency_id`, `ezidapp_shoulder`.`prefix_shares_datacenter`, `ezidapp_shoulder`.`manager`, `ezidapp_shoulder`.`active`, `ezidapp_shoulder`.`redirect`, `ezidapp_shoulder`.`date`, `ezidapp_shoulder`.`isSupershoulder`
FROM `ezidapp_shoulder`
INNER JOIN `ezidapp_user_shoulders`
ON (`ezidapp_shoulder`.`id` = `ezidapp_user_shoulders`.`shoulder_id`)
WHERE `ezidapp_user_shoulders`.`user_id` IN (1);

select * from ezidapp_user_shoulders order by user_id;


# Orig:
select id from ezidapp_searchuser es order by id;
# -> 1,2,10,13,14,21,26,28,30,31,39,40,48,52,53,69,75,80,89,93,96,99,101,102,104,108,111,114,116,117,118,119,120,123,124,126,130,131,135,136,137,139,140,145,152,159,160,166,171,173,175,180,186,187,188,191,192,193,195,199,204,206,207,210,211,213,214,216,219,222,225,227,228,229,230,232,235,236,237,239,241,244,245,246,249,252,261,268,269,271,272,276,277,279,281,282,284,285,286,287,290,292,297,298,300,307,308,309,310,311,316,320,323,324,326,327,328,333,334,337,338,340,342,344,345,349,350,351,354,358,359,361,362,363,365,366,371,372,375,378,379,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,403,404,406,407,408,409,410,411,415,416,417,418,419,420,422,423,424,426,427,428,429,430,431,432,433,434,435,436,437,438,439,440,441,443,444,445,446,447,448,449,450,451,452,453,454,455,456,457,458,459,460,461,462,463,464,465,466,468,469,470,471,472,473,474,475,476,477,478
select id from ezidapp_storeuser e order by id;
# -> 1,2,9,10,11,15,22,23,25,26,39,44,49,52,56,57,59,60,65,66,67,70,75,87,98,99,100,105,107,108,109,110,111,124,130,134,139,152,163,170,172,179,180,181,182,183,184,185,186,195,196,198,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,216,217,219,220,221,222,223,224,225,226,227,228,229,230,231,232,233,234,235,237,238,240,241,242,243,244,245,246,247,248,268,275,289,290,292,295,296,298,305,306,307,308,309,314,318,321,322,324,325,326,331,332,335,336,338,340,342,343,347,348,349,352,356,357,359,360,361,363,364,369,370,373,376,377,384,385,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,404,405,406,407,408,409,413,414,415,416,417,418,420,421,422,424,425,426,427,428,429,430,431,432,433,434,435,437,438,439,440,442,443,444,445,446,447,448,449,450,451,452,453,454,455,456,457,458,459,460,461,462,463,464,465,467,468,469,470,471,472,473,474,475,476,477

select count(*) from ezidapp_user_proxies eup where eup.from_user_id not in (1,2,9,10,11,15,22,23,25,26,39,44,49,52,56,57,59,60,65,66,67,70,75,87,98,99,100,105,107,108,109,110,111,124,130,134,139,152,163,170,172,179,180,181,182,183,184,185,186,195,196,198,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,216,217,219,220,221,222,223,224,225,226,227,228,229,230,231,232,233,234,235,237,238,240,241,242,243,244,245,246,247,248,268,275,289,290,292,295,296,298,305,306,307,308,309,314,318,321,322,324,325,326,331,332,335,336,338,340,342,343,347,348,349,352,356,357,359,360,361,363,364,369,370,373,376,377,384,385,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,404,405,406,407,408,409,413,414,415,416,417,418,420,421,422,424,425,426,427,428,429,430,431,432,433,434,435,437,438,439,440,442,443,444,445,446,447,448,449,450,451,452,453,454,455,456,457,458,459,460,461,462,463,464,465,467,468,469,470,471,472,473,474,475,476,477)
;
select count(*) from ezidapp_user_proxies eup where eup.to_user_id not in (1,2,9,10,11,15,22,23,25,26,39,44,49,52,56,57,59,60,65,66,67,70,75,87,98,99,100,105,107,108,109,110,111,124,130,134,139,152,163,170,172,179,180,181,182,183,184,185,186,195,196,198,200,201,202,203,204,205,206,207,208,209,210,211,212,213,214,216,217,219,220,221,222,223,224,225,226,227,228,229,230,231,232,233,234,235,237,238,240,241,242,243,244,245,246,247,248,268,275,289,290,292,295,296,298,305,306,307,308,309,314,318,321,322,324,325,326,331,332,335,336,338,340,342,343,347,348,349,352,356,357,359,360,361,363,364,369,370,373,376,377,384,385,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,404,405,406,407,408,409,413,414,415,416,417,418,420,421,422,424,425,426,427,428,429,430,431,432,433,434,435,437,438,439,440,442,443,444,445,446,447,448,449,450,451,452,453,454,455,456,457,458,459,460,461,462,463,464,465,467,468,469,470,471,472,473,474,475,476,477)
;

select count(*) from ezidapp_user_shoulders where user_id not in (select id from ezidapp_user eu);
select count(*) from ezidapp_user_shoulders where shoulder_id not in (select id from ezidapp_shoulder es);

show create table ezidapp_user_shoulders;
CREATE TABLE `ezidapp_user_shoulders` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `shoulder_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `storeuser_id` (`user_id`,`shoulder_id`),
  KEY `ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id` (`shoulder_id`),
  CONSTRAINT `ezidapp_st_storeuser_id_6730d06357e88738_fk_ezidapp_storeuser_id` FOREIGN KEY (`user_id`) REFERENCES `ezidapp_user` (`id`),
  CONSTRAINT `ezidapp_stor_shoulder_id_760fcf030c9067e7_fk_ezidapp_shoulder_id` FOREIGN KEY (`shoulder_id`) REFERENCES `ezidapp_shoulder` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=9514 DEFAULT CHARSET=utf8


select count(*) from ezidapp_user_proxies eup where eup.to_user_id not in (select id from ezidapp_user eu);
select * from ezidapp_user_proxies;
select * from ezidapp_user_proxies eup where eup.from_user_id not in (1,2,10,13,14,21,26,28,30,31,39,40,48,52,53,69,75,80,89,93,96,99,101,102,104,108,111,114,116,117,118,119,120,123,124,126,130,131,135,136,137,139,140,145,152,159,160,166,171,173,175,180,186,187,188,191,192,193,195,199,204,206,207,210,211,213,214,216,219,222,225,227,228,229,230,232,235,236,237,239,241,244,245,246,249,252,261,268,269,271,272,276,277,279,281,282,284,285,286,287,290,292,297,298,300,307,308,309,310,311,316,320,323,324,326,327,328,333,334,337,338,340,342,344,345,349,350,351,354,358,359,361,362,363,365,366,371,372,375,378,379,386,387,388,389,390,391,392,393,394,395,396,397,398,399,400,401,402,403,404,406,407,408,409,410,411,415,416,417,418,419,420,422,423,424,426,427,428,429,430,431,432,433,434,435,436,437,438,439,440,441,443,444,445,446,447,448,449,450,451,452,453,454,455,456,457,458,459,460,461,462,463,464,465,466,468,469,470,471,472,473,474,475,476,477,478);
update ezidapp_user_proxies set
    from_user_id = case when 1 then 1 when 2 then 2 when 10 then 75 when 13 then 243 when 14 then 248 when 21 then 186 when 26 then 223 when 28 then 65 when 30 then 240 when 31 then 202 when 39 then 66 when 40 then 87 when 48 then 184 when 52 then 152 when 53 then 242 when 69 then 247 when 75 then 44 when 80 then 182 when 89 then 111 when 93 then 233 when 96 then 212 when 99 then 230 when 101 then 185 when 102 then 57 when 104 then 110 when 108 then 214 when 111 then 163 when 114 then 207 when 116 then 228 when 117 then 275 when 118 then 60 when 119 then 208 when 120 then 213 when 123 then 198 when 124 then 209 when 126 then 179 when 130 then 22 when 131 then 59 when 135 then 204 when 136 then 289 when 137 then 39 when 139 then 134 when 140 then 172 when 145 then 180 when 152 then 26 when 159 then 9 when 160 then 234 when 166 then 238 when 171 then 15 when 173 then 220 when 175 then 201 when 180 then 244 when 186 then 237 when 187 then 139 when 188 then 210 when 191 then 211 when 192 then 232 when 193 then 130 when 195 then 245 when 199 then 226 when 204 then 56 when 206 then 100 when 207 then 227 when 210 then 23 when 211 then 268 when 213 then 49 when 214 then 235 when 216 then 98 when 219 then 181 when 222 then 195 when 225 then 231 when 227 then 216 when 228 then 52 when 229 then 25 when 230 then 124 when 232 then 217 when 235 then 170 when 236 then 219 when 237 then 241 when 239 then 67 when 241 then 206 when 244 then 225 when 245 then 196 when 246 then 205 when 249 then 99 when 252 then 70 when 261 then 183 when 268 then 108 when 269 then 203 when 271 then 246 when 272 then 229 when 276 then 109 when 277 then 10 when 279 then 292 when 281 then 105 when 282 then 11 when 284 then 222 when 285 then 221 when 286 then 224 when 287 then 200 when 290 then 107 when 292 then 290 when 297 then 295 when 298 then 296 when 300 then 298 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 when 311 then 309 when 316 then 314 when 320 then 318 when 323 then 321 when 324 then 322 when 326 then 324 when 327 then 325 when 328 then 326 when 333 then 331 when 334 then 332 when 337 then 335 when 338 then 336 when 340 then 338 when 342 then 340 when 344 then 342 when 345 then 343 when 349 then 347 when 350 then 348 when 351 then 349 when 354 then 352 when 358 then 356 when 359 then 357 when 361 then 359 when 362 then 360 when 363 then 361 when 365 then 363 when 366 then 364 when 371 then 369 when 372 then 370 when 375 then 373 when 378 then 376 when 379 then 377 when 386 then 384 when 387 then 385 when 388 then 386 when 389 then 387 when 390 then 388 when 391 then 389 when 392 then 390 when 393 then 391 when 394 then 392 when 395 then 393 when 396 then 394 when 397 then 395 when 398 then 396 when 399 then 397 when 400 then 398 when 401 then 399 when 402 then 400 when 403 then 401 when 404 then 402 when 406 then 404 when 407 then 405 when 408 then 406 when 409 then 407 when 410 then 408 when 411 then 409 when 415 then 413 when 416 then 414 when 417 then 415 when 418 then 416 when 419 then 417 when 420 then 418 when 422 then 420 when 423 then 421 when 424 then 422 when 426 then 424 when 427 then 425 when 428 then 426 when 429 then 427 when 430 then 428 when 431 then 429 when 432 then 430 when 433 then 431 when 434 then 432 when 435 then 433 when 436 then 434 when 437 then 435 when 438 then 437 when 439 then 438 when 440 then 439 when 441 then 440 when 443 then 442 when 444 then 443 when 445 then 444 when 446 then 445 when 447 then 446 when 448 then 447 when 449 then 448 when 450 then 449 when 451 then 450 when 452 then 451 when 453 then 452 when 454 then 453 when 455 then 454 when 456 then 455 when 457 then 456 when 458 then 457 when 459 then 458 when 460 then 459 when 461 then 460 when 462 then 461 when 463 then 462 when 464 then 463 when 465 then 464 when 466 then 465 when 468 then 467 when 469 then 468 when 470 then 469 when 471 then 470 when 472 then 471 when 473 then 472 when 474 then 473 when 475 then 474 when 476 then 475 when 477 then 476 when 478 then 477 end,
    to_user_id =   case when 1 then 1 when 2 then 2 when 10 then 75 when 13 then 243 when 14 then 248 when 21 then 186 when 26 then 223 when 28 then 65 when 30 then 240 when 31 then 202 when 39 then 66 when 40 then 87 when 48 then 184 when 52 then 152 when 53 then 242 when 69 then 247 when 75 then 44 when 80 then 182 when 89 then 111 when 93 then 233 when 96 then 212 when 99 then 230 when 101 then 185 when 102 then 57 when 104 then 110 when 108 then 214 when 111 then 163 when 114 then 207 when 116 then 228 when 117 then 275 when 118 then 60 when 119 then 208 when 120 then 213 when 123 then 198 when 124 then 209 when 126 then 179 when 130 then 22 when 131 then 59 when 135 then 204 when 136 then 289 when 137 then 39 when 139 then 134 when 140 then 172 when 145 then 180 when 152 then 26 when 159 then 9 when 160 then 234 when 166 then 238 when 171 then 15 when 173 then 220 when 175 then 201 when 180 then 244 when 186 then 237 when 187 then 139 when 188 then 210 when 191 then 211 when 192 then 232 when 193 then 130 when 195 then 245 when 199 then 226 when 204 then 56 when 206 then 100 when 207 then 227 when 210 then 23 when 211 then 268 when 213 then 49 when 214 then 235 when 216 then 98 when 219 then 181 when 222 then 195 when 225 then 231 when 227 then 216 when 228 then 52 when 229 then 25 when 230 then 124 when 232 then 217 when 235 then 170 when 236 then 219 when 237 then 241 when 239 then 67 when 241 then 206 when 244 then 225 when 245 then 196 when 246 then 205 when 249 then 99 when 252 then 70 when 261 then 183 when 268 then 108 when 269 then 203 when 271 then 246 when 272 then 229 when 276 then 109 when 277 then 10 when 279 then 292 when 281 then 105 when 282 then 11 when 284 then 222 when 285 then 221 when 286 then 224 when 287 then 200 when 290 then 107 when 292 then 290 when 297 then 295 when 298 then 296 when 300 then 298 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 when 311 then 309 when 316 then 314 when 320 then 318 when 323 then 321 when 324 then 322 when 326 then 324 when 327 then 325 when 328 then 326 when 333 then 331 when 334 then 332 when 337 then 335 when 338 then 336 when 340 then 338 when 342 then 340 when 344 then 342 when 345 then 343 when 349 then 347 when 350 then 348 when 351 then 349 when 354 then 352 when 358 then 356 when 359 then 357 when 361 then 359 when 362 then 360 when 363 then 361 when 365 then 363 when 366 then 364 when 371 then 369 when 372 then 370 when 375 then 373 when 378 then 376 when 379 then 377 when 386 then 384 when 387 then 385 when 388 then 386 when 389 then 387 when 390 then 388 when 391 then 389 when 392 then 390 when 393 then 391 when 394 then 392 when 395 then 393 when 396 then 394 when 397 then 395 when 398 then 396 when 399 then 397 when 400 then 398 when 401 then 399 when 402 then 400 when 403 then 401 when 404 then 402 when 406 then 404 when 407 then 405 when 408 then 406 when 409 then 407 when 410 then 408 when 411 then 409 when 415 then 413 when 416 then 414 when 417 then 415 when 418 then 416 when 419 then 417 when 420 then 418 when 422 then 420 when 423 then 421 when 424 then 422 when 426 then 424 when 427 then 425 when 428 then 426 when 429 then 427 when 430 then 428 when 431 then 429 when 432 then 430 when 433 then 431 when 434 then 432 when 435 then 433 when 436 then 434 when 437 then 435 when 438 then 437 when 439 then 438 when 440 then 439 when 441 then 440 when 443 then 442 when 444 then 443 when 445 then 444 when 446 then 445 when 447 then 446 when 448 then 447 when 449 then 448 when 450 then 449 when 451 then 450 when 452 then 451 when 453 then 452 when 454 then 453 when 455 then 454 when 456 then 455 when 457 then 456 when 458 then 457 when 459 then 458 when 460 then 459 when 461 then 460 when 462 then 461 when 463 then 462 when 464 then 463 when 465 then 464 when 466 then 465 when 468 then 467 when 469 then 468 when 470 then 469 when 471 then 470 when 472 then 471 when 473 then 472 when 474 then 473 when 475 then 474 when 476 then 475 when 477 then 476 when 478 then 477 end
;
alter table ezidapp_user_proxies
drop foreign key `ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id`
;

alter table ezidapp_user_proxies
drop foreign key `ezida_from_storeuser_id_199e0c23a1cd56a7_fk_ezidapp_storeuser_id`
;

alter table ezidapp_user_proxies
drop key from_storeuser_id
;

# alter table ezidapp_user_proxies
# add UNIQUE KEY `from_storeuser_id` (`from_user_id`, `to_user_id`)
# ;

select * from ezidapp_user_proxies;

drop table ezidapp_user_proxies;

CREATE TABLE `ezidapp_user_proxies` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `from_user_id` int(11) DEFAULT NULL,
  `to_user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `from_storeuser_id` (`from_user_id`,`to_user_id`),
  KEY `ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id` (`to_user_id`),
  CONSTRAINT `ezida_from_storeuser_id_199e0c23a1cd56a7_fk_ezidapp_storeuser_id` FOREIGN KEY (`from_user_id`) REFERENCES `ezidapp_user` (`id`),
  CONSTRAINT `ezidapp_to_storeuser_id_74856b12f826a792_fk_ezidapp_storeuser_id` FOREIGN KEY (`to_user_id`) REFERENCES `ezidapp_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=487 DEFAULT CHARSET=utf8
;


# Replace
# ((when \d+ then \d+ ){10})
# $1\n

# user
# 27min on RDS
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchuser a join ezidapp_storeuser b on a.pid = b.pid
order by a.id
;
# ->  when 1 then 1 when 2 then 2 when 10 then 75 when 13 then 243 when 14 then 248 when 21 then 186 when 26 then 223 when 28 then 65 when 30 then 240 when 31 then 202 when 39 then 66 when 40 then 87 when 48 then 184 when 52 then 152 when 53 then 242 when 69 then 247 when 75 then 44 when 80 then 182 when 89 then 111 when 93 then 233 when 96 then 212 when 99 then 230 when 101 then 185 when 102 then 57 when 104 then 110 when 108 then 214 when 111 then 163 when 114 then 207 when 116 then 228 when 117 then 275 when 118 then 60 when 119 then 208 when 120 then 213 when 123 then 198 when 124 then 209 when 126 then 179 when 130 then 22 when 131 then 59 when 135 then 204 when 136 then 289 when 137 then 39 when 139 then 134 when 140 then 172 when 145 then 180 when 152 then 26 when 159 then 9 when 160 then 234 when 166 then 238 when 171 then 15 when 173 then 220 when 175 then 201 when 180 then 244 when 186 then 237 when 187 then 139 when 188 then 210 when 191 then 211 when 192 then 232 when 193 then 130 when 195 then 245 when 199 then 226 when 204 then 56 when 206 then 100 when 207 then 227 when 210 then 23 when 211 then 268 when 213 then 49 when 214 then 235 when 216 then 98 when 219 then 181 when 222 then 195 when 225 then 231 when 227 then 216 when 228 then 52 when 229 then 25 when 230 then 124 when 232 then 217 when 235 then 170 when 236 then 219 when 237 then 241 when 239 then 67 when 241 then 206 when 244 then 225 when 245 then 196 when 246 then 205 when 249 then 99 when 252 then 70 when 261 then 183 when 268 then 108 when 269 then 203 when 271 then 246 when 272 then 229 when 276 then 109 when 277 then 10 when 279 then 292 when 281 then 105 when 282 then 11 when 284 then 222 when 285 then 221 when 286 then 224 when 287 then 200 when 290 then 107 when 292 then 290 when 297 then 295 when 298 then 296 when 300 then 298 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 when 311 then 309 when 316 then 314 when 320 then 318 when 323 then 321 when 324 then 322 when 326 then 324 when 327 then 325 when 328 then 326 when 333 then 331 when 334 then 332 when 337 then 335 when 338 then 336 when 340 then 338 when 342 then 340 when 344 then 342 when 345 then 343 when 349 then 347 when 350 then 348 when 351 then 349 when 354 then 352 when 358 then 356 when 359 then 357 when 361 then 359 when 362 then 360 when 363 then 361 when 365 then 363 when 366 then 364 when 371 then 369 when 372 then 370 when 375 then 373 when 378 then 376 when 379 then 377 when 386 then 384 when 387 then 385 when 388 then 386 when 389 then 387 when 390 then 388 when 391 then 389 when 392 then 390 when 393 then 391 when 394 then 392 when 395 then 393 when 396 then 394 when 397 then 395 when 398 then 396 when 399 then 397 when 400 then 398 when 401 then 399 when 402 then 400 when 403 then 401 when 404 then 402 when 406 then 404 when 407 then 405 when 408 then 406 when 409 then 407 when 410 then 408 when 411 then 409 when 415 then 413 when 416 then 414 when 417 then 415 when 418 then 416 when 419 then 417 when 420 then 418 when 422 then 420 when 423 then 421 when 424 then 422 when 426 then 424 when 427 then 425 when 428 then 426 when 429 then 427 when 430 then 428 when 431 then 429 when 432 then 430 when 433 then 431 when 434 then 432 when 435 then 433 when 436 then 434 when 437 then 435 when 438 then 437 when 439 then 438 when 440 then 439 when 441 then 440 when 443 then 442 when 444 then 443 when 445 then 444 when 446 then 445 when 447 then 446 when 448 then 447 when 449 then 448 when 450 then 449 when 451 then 450 when 452 then 451 when 453 then 452 when 454 then 453 when 455 then 454 when 456 then 455 when 457 then 456 when 458 then 457 when 459 then 458 when 460 then 459 when 461 then 460 when 462 then 461 when 463 then 462 when 464 then 463 when 465 then 464 when 466 then 465 when 468 then 467 when 469 then 468 when 470 then 469 when 471 then 470 when 472 then 471 when 473 then 472 when 474 then 473 when 475 then 474 when 476 then 475 when 477 then 476 when 478 then 477

# group
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchgroup a join ezidapp_storegroup b on a.pid = b.pid
order by a.id
;
# -> when 1 then 1 when 2 then 2 when 3 then 223 when 7 then 28 when 10 then 21 when 13 then 263 when 22 then 196 when 27 then 84 when 35 then 172 when 38 then 23 when 39 then 145 when 50 then 186 when 53 then 57 when 55 then 121 when 75 then 112 when 94 then 202 when 108 then 247 when 110 then 187 when 117 then 190 when 125 then 203 when 137 then 14 when 147 then 199 when 153 then 51 when 158 then 106 when 161 then 171 when 176 then 159 when 177 then 22 when 185 then 47 when 200 then 224 when 206 then 116 when 211 then 242 when 215 then 192 when 220 then 92 when 235 then 39 when 251 then 10 when 265 then 264 when 275 then 273 when 283 then 281 when 288 then 286 when 292 then 290 when 296 then 294 when 297 then 295 when 299 then 297 when 301 then 299 when 303 then 301 when 304 then 302 when 305 then 303 when 306 then 304 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308

# profile
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchprofile a join ezidapp_storeprofile b on a.label = b.label
order by a.id
;
# ->  when 1 then 1 when 2 then 3 when 3 then 2 when 4 then 5 when 5 then 4 when 8 then 8 when 9 then 9 when 11 then 11 when 12 then 12 when 13 then 13

# datacenter
select concat(' when ', a.id, ' then ', b.id)
from ezidapp_searchdatacenter a join ezidapp_storedatacenter b on a.symbol = b.symbol
order by a.id
;
# -> when 7 then 1 when 9 then 207 when 15 then 9 when 24 then 181 when 27 then 205 when 29 then 158 when 47 then 182 when 56 then 208 when 180 then 184 when 223 then 266 when 224 then 267

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

# Order of importance for keys was found by running this query on the production database:
#
# select count_star, index_name
# from performance_schema.table_io_waits_summary_by_index_usage
# where object_name='ezidapp_searchidentifier'
# group by count_star, index_name
# order by count_star desc;

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

-- Unused keys
-- add key `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx`(`owner_id`, `isTest`),
-- add key `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx`(`owner_id`, `resourcePublisherPrefix`),
-- add key `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx`(`ownergroup_id`, `status`),
-- add key `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx`(`ownergroup_id`, `searchableResourceType`),
-- add key `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx`(`ownergroup_id`, `hasMetadata`),
-- add key `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx`(`ownergroup_id`, `resourceCreatorPrefix`),
-- add key `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx`(`ownergroup_id`, `resourcePublisherPrefix`),
-- add key `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx`(`publicSearchVisible`, `updateTime`),
-- add key `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx`(`publicSearchVisible`, `resourceCreatorPrefix`),
-- add key `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx`(`publicSearchVisible`, `resourceTitlePrefix`),
-- add key `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx`(`publicSearchVisible`, `resourcePublisherPrefix`),
-- add key `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx`(`searchableTarget`),
