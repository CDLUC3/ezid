/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

# Prepare database for capturing as a DB fixture.
#
# The large tables in the DB are trimmed down by randomly removing all but 0.1% of the rows.
#
# See README.md for how to use this file.

# Run query in small batches to prevent transactions spilling to disk and slowing things down.
# http://mysql.rjweb.org/doc.php/deletebig
# https://stackoverflow.com/questions/14284238/how-can-i-improve-delete-from-performance-on-large-innodb-tables

drop procedure if exists trim_searchidentifier;

delimiter $$
create procedure trim_searchidentifier()
begin
    declare last_id int default 0;
    declare max_id int;
    select max(id) into max_id from ezidapp_searchidentifier;
    x:
    loop
        delete
        from ezidapp_searchidentifier
        where rand() > 0.1
#         # 0.0001 = .01% average = ~2500 rows
#         where rand() > 0.0001
        and id = last_insert_id(id)
        and id > last_id
        limit 10000
        ;

        select concat('last_id: ', (select last_id)) as 'progress';
        set last_id = last_insert_id();
        if (last_id = max_id) then leave x; end if;
    end loop;
end;
delimiter ;

call trim_searchidentifier();

# Check how many rows remain.
select count(*) from ezidapp_searchidentifier;

# Limit store identifiers to match those that remain in search.

drop procedure if exists trim_identifier;

delimiter $$
create procedure trim_identifier()
begin
    declare c int default 0;
    x:
    loop
        delete
        from ezidapp_identifier
        where identifier not in (select identifier from ezidapp_searchidentifier)
        limit 10000
        ;
        if (row_count() = 0) then leave x; end if;
        set c = c + 1;
        select c;
    end loop;
end;
delimiter ;

call trim_identifier();

# Check how many rows remain.
select count(*) from ezidapp_identifier;

# Limit the linker checker to contain state info only for the remaining identifiers.
# 30 min

drop procedure if exists trim_linkchecker;

delimiter $$
create procedure trim_linkchecker()
begin
    declare c int default 0;
    x:
    loop
        delete
        from ezidapp_linkchecker
        where identifier not in (select identifier from ezidapp_identifier)
        limit 10000
        ;
        if (row_count() = 0) then leave x; end if;
        set c = c + 1;
        select c;
    end loop;
end;
delimiter ;

call trim_linkchecker();

# Trim some smaller tables;

delete from ezidapp_statistics where month not regexp '^(2018|2019|2020|2021)-';
delete from django_admin_log;
delete from django_session;

# Drop / randomize user and group info

# User fields to keep unchanged
# id
# pid
# inheritGroupShoulders
# crossrefEnabled
# crossrefEmail
# isGroupAdministrator
# isRealmAdministrator
# isSuperuser
# loginEnabled
# group_id
# realm_id


update ezidapp_realm set name = 'CDL';

select * from ezidapp_searchrealm er;

UPDATE ezid.ezidapp_user SET pid = 'ark:/99166/p9kw57h4w', username = 'admin', displayName = 'admin', accountEmail = '', primaryContactName = '', primaryContactEmail = '', primaryContactPhone = '', secondaryContactName = '', secondaryContactEmail = '', secondaryContactPhone = '', inheritGroupShoulders = 0, crossrefEnabled = 1, crossrefEmail = '', isGroupAdministrator = 0, isRealmAdministrator = 0, isSuperuser = 1, loginEnabled = 1, password = 'pbkdf2_sha256$260000$YAGoSpofqXbbXhr3CXcuZU$MbzIkg/YCikvKe7vYNkUFls3clXkHYUkBh54HdZMRRA=', notes = '', group_id = 309, realm_id = 1 WHERE id = 1;
UPDATE ezid.ezidapp_user SET pid = 'ark:/99166/p9jq0st8j', username = 'apitest', displayName = 'EZID API test account', accountEmail = 'ezid@ucop.edu', primaryContactName = 'EZID administrator', primaryContactEmail = 'ezid@ucop.edu', primaryContactPhone = '(510) 987-0555', secondaryContactName = '', secondaryContactEmail = '', secondaryContactPhone = '', inheritGroupShoulders = 0, crossrefEnabled = 0, crossrefEmail = '', isGroupAdministrator = 0, isRealmAdministrator = 0, isSuperuser = 0, loginEnabled = 1, password = 'pbkdf2_sha256$20000$A7NrSMRv4gH8$2MwlthcX2Pljnzvgnnv4wUOjYKYXHg+lqN9D3dQ2Zfw=', notes = '', group_id = 2, realm_id = 1 WHERE id = 2;


# User fields to randomize
update ezidapp_user set
username=substr(md5(rand()), 1, 10),
displayname=substr(md5(rand()), 1, 10)
where username <> 'admin' and user <> 'apitest'
;

# User fields to clear
update ezidapp_user set
accountEmail='',
primaryContactName='',
primaryContactEmail='',
primaryContactPhone='',
secondaryContactName='',
secondaryContactEmail='',
secondaryContactPhone='',
notes='',
password=''
where username <> 'admin' and user <> 'apitest'
;

# Group fields to keep unchanged
# id
# pid
# agreementOnFile
# crossrefEnabled
# realm_id
# accountType

# Group fields to randomize
update ezidapp_group set
groupname=substr(md5(rand()), 1, 10)
;

# Group fields to clear
update ezidapp_group set
organizationName = '',
organizationAcronym = '',
organizationUrl = '',
organizationStreetAddress = '',
notes = ''
;

select * from ezidapp_realm;
update ezidapp_realm set name = 'CDL' where id = 1;


/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */


##############################################

# Check remaining rows counts

select
    (select count(*) from ezidapp_linkchecker) as link_checker,
    (select count(*) from django_admin_log) as admin_log,
    (select count(*) from ezidapp_searchidentifier es) as 'search',
    (select count(*) from ezidapp_searchidentifier es where metadata is not null) as 'search_metadata',
    (select count(*) from ezidapp_identifier es) as 'store',
    (select count(*) from ezidapp_identifier es where metadata is not null) as 'store_metadata'
;
