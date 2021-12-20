use ezid;

set unique_checks = 0;
set foreign_key_checks = 0;

# Add less used keys one by one, in order of importance.
# This step can run after EZID has been started.

# 93001201 | ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx`(`owner_id`, `updateTime`);
# 84129679 | ezidapp_searchidentifier_365b2611
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_365b2611`(`ownergroup_id`);
# 81640063 | ezidapp_searchidentifier_13bc2970
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_13bc2970`(`datacenter_id`);
# 71055879 | ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx`(`owner_id`, `identifier`);
# 64647693 | ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx`(`publicSearchVisible`, `searchablePublicationYear`);
# 60195608 | ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx`(`publicSearchVisible`, `createTime`);
# 59627193 | ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx`(`owner_id`, `searchableResourceType`);
# 30770472 | ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx`(`owner_id`, `createTime`);
# 27213349 | ezidapp_searchidentifier_83a0eb3f
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_83a0eb3f`(`profile_id`);
# 23410277 | ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx`(`ownergroup_id`, `updateTime`);
# 19388568 | ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx`(`owner_id`, `exported`);
# 14880395 | ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx`(`owner_id`, `profile_id`);
# 14274173 | ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx`(`ownergroup_id`, `hasIssues`);
# 14193439 | ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx`(`ownergroup_id`, `profile_id`);
# 11497247 | ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx`(`ownergroup_id`, `crossrefStatus`);
# 5411586 | ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx`(`owner_id`, `searchablePublicationYear`);
# 4652160 | ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx`(`ownergroup_id`, `resourceTitlePrefix`);
# 4298890 | ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx`(`ownergroup_id`, `identifier`);
# 3779471 | ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx`(`ownergroup_id`, `createTime`);
# 3023677 | ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx`(`owner_id`, `status`);
# 3001925 | ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx`(`owner_id`, `crossrefStatus`);
# 2991637 | ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx`(`ownergroup_id`, `searchablePublicationYear`);
# 2549026 | ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx`(`owner_id`, `hasIssues`);
# 1600118 | ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx`(`owner_id`, `resourceTitlePrefix`);
# 747300 | ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx`(`ownergroup_id`, `isTest`);
# 86164 | ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx`(`owner_id`, `resourceCreatorPrefix`);
# 35588 | ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx`(`ownergroup_id`, `exported`);
# 5492 | ezidapp_searchidentifier_owner_id_18a46334256a7530_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx`(`owner_id`, `hasMetadata`);
# 4718 | ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx`(`publicSearchVisible`, `searchableResourceType`);
# +------------+------------------------------------------------------------------+

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