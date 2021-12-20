use ezid;

set unique_checks = 0;
set foreign_key_checks = 0;

# Crate fulltext indexes (must be done one at a time). 30 min?
# EZID will not run without these indexes.
# This is the final step to run before starting EZID.

alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_keywords(keywords);
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcecreator(resourcecreator);
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcepublisher(resourcepublisher);
alter table ezidapp_searchidentifier add fulltext ezidapp_searchidentifier_resourcetitle(resourcetitle);

# Create foreign key constraints. 10 min
alter table ezidapp_searchidentifier
add constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_storeuser` (`id`),
add constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_storegroup` (`id`),
add constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_storeprofile` (`id`),
add constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_storedatacenter` (`id`)
;

# Add the most used keys, using a batch query

# 1694234344 | ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx
# 1470014804 | ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx
#  211448890 | ezidapp_searchidentifier_5e7b1936
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx`(`publicSearchVisible`, `identifier`),
add key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx`(`oaiVisible`, `updateTime`),
add key `ezidapp_searchidentifier_5e7b1936`(`owner_id`)
;
