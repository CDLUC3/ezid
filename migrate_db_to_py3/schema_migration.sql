/*
 * Copyright©2021, Regents of the University of California
 * http://creativecommons.org/licenses/BSD
 */

use ezid;

# Rename tables to remove all 'store' prefixes.
rename table ezidapp_storedatacenter to ezidapp_datacenter;
rename table ezidapp_storegroup to ezidapp_group;
rename table ezidapp_storegroup_shoulders to ezidapp_group_shoulders;
rename table ezidapp_storeidentifier to ezidapp_identifier;
rename table ezidapp_storeprofile to ezidapp_profile;
rename table ezidapp_storerealm to ezidapp_realm;
rename table ezidapp_storeuser to ezidapp_user;
rename table ezidapp_storeuser_proxies to ezidapp_user_proxies;
rename table ezidapp_storeuser_shoulders to ezidapp_user_shoulders;

# Drop the 'stub' tables that exist only to support ezidapp_searchidentifier when located in another DB.
# These tables contain copies of some of the columns in the corresponding store* tables. The only search*
# table that remains afterwards is ezidapp_searchidentifier.
drop table ezidapp_searchdatacenter;
drop table ezidapp_searchgroup;
drop table ezidapp_searchprofile;
drop table ezidapp_searchrealm;
drop table ezidapp_searchuser;

# Drop everything that may slow down operations on ezidapp_searchidentifier

# Drop foreign key constrants first, to enable dropping the associated indexes
alter table ezidapp_searchidentifier
drop constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id`,
drop constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id`,
drop constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id`,
drop constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id`
;

# Drop keys and indexes (all except for the id and identifier indexes)
alter table ezidapp_searchidentifier
drop index ezidapp_searchidentifie_publicsearchvisible_117042133b78a88e_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_1932465b0335635c_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_1e447c57e83c8d5d_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_2e067bd0a9494a38_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_47396846c619370f_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_47b0a294295f5ef5_idx
, drop index ezidapp_searchidentifie_publicsearchvisible_58de9f6f00b8058e_idx
, drop index ezidapp_searchidentifier_13bc2970
, drop index ezidapp_searchidentifier_365b2611
, drop index ezidapp_searchidentifier_5e7b1936
, drop index ezidapp_searchidentifier_83a0eb3f
, drop index ezidapp_searchidentifier_oaivisible_1d291a23fcff2ce2_idx
, drop index ezidapp_searchidentifier_owner_id_18a46334256a7530_idx
, drop index ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx
, drop index ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx
, drop index ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx
, drop index ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx
, drop index ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx
, drop index ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx
, drop index ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx
, drop index ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx
, drop index ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx
, drop index ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx
, drop index ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx
, drop index ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx
, drop index ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx
, drop index ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx
, drop index ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx
, drop index ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx
, drop index ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx
, drop index ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx
, drop index ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx
, drop index ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx
, drop index ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx
, drop index ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx
, drop index ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx
, drop index ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx
, drop index ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx
, drop index ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx
, drop index ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx
, drop index ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx
, drop index ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx
, drop index ezidapp_searchidentifier_publicsearchvisible_6807647c6d8cb52_idx
, drop index ezidapp_searchidentifier_searchabletarget_24d34538786996df_idx
, drop key ezidapp_searchidentifier_keywords
, drop key ezidapp_searchidentifier_resourcecreator
, drop key ezidapp_searchidentifier_resourcepublisher
, drop key ezidapp_searchidentifier_resourcetitle
;

# Translate from search to store keys

# user
update ezidapp_searchidentifier set owner_id = case
when 1 then 1 when 2 then 2 when 10 then 75 when 13 then 243 when 14 then 248 when 21 then 186 when 26 then 223 when 28 then 65 when 30 then 240 when 31 then 202
when 39 then 66 when 40 then 87 when 48 then 184 when 52 then 152 when 53 then 242 when 69 then 247 when 75 then 44 when 80 then 182 when 89 then 111 when 93 then 233
when 96 then 212 when 99 then 230 when 101 then 185 when 102 then 57 when 104 then 110 when 108 then 214 when 111 then 163 when 114 then 207 when 116 then 228 when 117 then 275
when 118 then 60 when 119 then 208 when 120 then 213 when 123 then 198 when 124 then 209 when 126 then 179 when 130 then 22 when 131 then 59 when 135 then 204 when 136 then 289
when 137 then 39 when 139 then 134 when 140 then 172 when 145 then 180 when 152 then 26 when 159 then 9 when 160 then 234 when 166 then 238 when 171 then 15 when 173 then 220
when 175 then 201 when 180 then 244 when 186 then 237 when 187 then 139 when 188 then 210 when 191 then 211 when 192 then 232 when 193 then 130 when 195 then 245 when 199 then 226
when 204 then 56 when 206 then 100 when 207 then 227 when 210 then 23 when 211 then 268 when 213 then 49 when 214 then 235 when 216 then 98 when 219 then 181 when 222 then 195
when 225 then 231 when 227 then 216 when 228 then 52 when 229 then 25 when 230 then 124 when 232 then 217 when 235 then 170 when 236 then 219 when 237 then 241 when 239 then 67
when 241 then 206 when 244 then 225 when 245 then 196 when 246 then 205 when 249 then 99 when 252 then 70 when 261 then 183 when 268 then 108 when 269 then 203 when 271 then 246
when 272 then 229 when 276 then 109 when 277 then 10 when 279 then 292 when 281 then 105 when 282 then 11 when 284 then 222 when 285 then 221 when 286 then 224 when 287 then 200
when 290 then 107 when 292 then 290 when 297 then 295 when 298 then 296 when 300 then 298 when 307 then 305 when 308 then 306 when 309 then 307 when 310 then 308 when 311 then 309
when 316 then 314 when 320 then 318 when 323 then 321 when 324 then 322 when 326 then 324 when 327 then 325 when 328 then 326 when 333 then 331 when 334 then 332 when 337 then 335
when 338 then 336 when 340 then 338 when 342 then 340 when 344 then 342 when 345 then 343 when 349 then 347 when 350 then 348 when 351 then 349 when 354 then 352 when 358 then 356
when 359 then 357 when 361 then 359 when 362 then 360 when 363 then 361 when 365 then 363 when 366 then 364 when 371 then 369 when 372 then 370 when 375 then 373 when 378 then 376
when 379 then 377 when 386 then 384 when 387 then 385 when 388 then 386 when 389 then 387 when 390 then 388 when 391 then 389 when 392 then 390 when 393 then 391 when 394 then 392
when 395 then 393 when 396 then 394 when 397 then 395 when 398 then 396 when 399 then 397 when 400 then 398 when 401 then 399 when 402 then 400 when 403 then 401 when 404 then 402
when 406 then 404 when 407 then 405 when 408 then 406 when 409 then 407 when 410 then 408 when 411 then 409 when 415 then 413 when 416 then 414 when 417 then 415 when 418 then 416
when 419 then 417 when 420 then 418 when 422 then 420 when 423 then 421 when 424 then 422 when 426 then 424 when 427 then 425 when 428 then 426 when 429 then 427 when 430 then 428
when 431 then 429 when 432 then 430 when 433 then 431 when 434 then 432 when 435 then 433 when 436 then 434 when 437 then 435 when 438 then 437 when 439 then 438 when 440 then 439
when 441 then 440 when 443 then 442 when 444 then 443 when 445 then 444 when 446 then 445 when 447 then 446 when 448 then 447 when 449 then 448 when 450 then 449 when 451 then 450
when 452 then 451 when 453 then 452 when 454 then 453 when 455 then 454 when 456 then 455 when 457 then 456 when 458 then 457 when 459 then 458 when 460 then 459 when 461 then 460
when 462 then 461 when 463 then 462 when 464 then 463 when 465 then 464 when 466 then 465 when 468 then 467 when 469 then 468 when 470 then 469 when 471 then 470 when 472 then 471
when 473 then 472 when 474 then 473 when 475 then 474 when 476 then 475 when 477 then 476 when 478 then 477 end
;

# group
update ezidapp_searchidentifier set ownergroup_id = case
when 1 then 1  when 2 then 2  when 3 then 223  when 7 then 28  when 10 then 21  when 13 then 263  when 22 then 196  when 27 then 84  when 35 then 172  when 38 then 23
when 39 then 145  when 50 then 186  when 53 then 57  when 55 then 121  when 75 then 112  when 94 then 202  when 108 then 247  when 110 then 187  when 117 then 190  when 125 then 203
when 137 then 14  when 147 then 199  when 153 then 51  when 158 then 106  when 161 then 171  when 176 then 159  when 177 then 22  when 185 then 47  when 200 then 224  when 206 then 116
when 211 then 242  when 215 then 192  when 220 then 92  when 235 then 39  when 251 then 10  when 265 then 264  when 275 then 273  when 283 then 281  when 288 then 286  when 292 then 290
when 296 then 294  when 297 then 295  when 299 then 297  when 301 then 299  when 303 then 301  when 304 then 302  when 305 then 303  when 306 then 304  when 307 then 305  when 308 then 306
when 309 then 307  when 310 then 308 end
;

# profile
update ezidapp_searchidentifier set profile_id = case
when 1 then 1  when 2 then 3  when 3 then 2  when 4 then 5  when 5 then 4  when 8 then 8  when 9 then 9  when 11 then 11  when 12 then 12  when 13 then 13 end
;

# datacenter
update ezidapp_searchidentifier set datacenter_id = case
when 1 then 297  when 7 then 1  when 9 then 207  when 15 then 9  when 24 then 181  when 27 then 205  when 29 then 158  when 47 then 182  when 56 then 208  when 97 then 303
when 111 then 300  when 124 then 304  when 139 then 302  when 174 then 299  when 180 then 184  when 196 then 298  when 200 then 301  when 209 then 305  when 223 then 266  when 224 then 267
end
;


# Add JSON metadata columns

alter table `ezidapp_searchidentifier`
add column metadata json default null
;
alter table `ezidapp_storeidentifier`
add column metadata json default null
;
update ezidapp_searchidentifier
set metadata = '{}'
;
update ezidapp_storeidentifier
set metadata = '{}'
;

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

# Add constraints back, in order of importance

# !!! The optimal order has not been determined yet !!!

alter table ezidapp_searchidentifier
add constraint `ezidapp_searc_owner_id_17d8ce4cfb6b0401_fk_ezidapp_searchuser_id` foreign key (`owner_id`) references `ezidapp_storeuser` (`id`)
;
alter table ezidapp_searchidentifier
add constraint `ezidapp_ownergroup_id_69f5065adf48f369_fk_ezidapp_searchgroup_id` foreign key (`ownergroup_id`) references `ezidapp_storegroup` (`id`)
;
alter table ezidapp_searchidentifier
add constraint `ezidapp__profile_id_112e6b8634f63b63_fk_ezidapp_searchprofile_id` foreign key (`profile_id`) references `ezidapp_storeprofile` (`id`)
;
alter table ezidapp_searchidentifier
add constraint `ez_datacenter_id_2c99a133444936c8_fk_ezidapp_searchdatacenter_id` foreign key (`datacenter_id`) references `ezidapp_storedatacenter` (`id`)
;


create fulltext index ezidapp_searchidentifier_keywords
on ezidapp_searchidentifier(keywords)
;
create fulltext index ezidapp_searchidentifier_resourcecreator
on ezidapp_searchidentifier(resourcecreator)
;
create fulltext index ezidapp_searchidentifier_resourcepublisher
on ezidapp_searchidentifier(resourcepublisher)
;
create fulltext index ezidapp_searchidentifier_resourcetitle
on ezidapp_searchidentifier(resourcetitle)
;

alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_5e7b1936`(`owner_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_365b2611`(`ownergroup_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_13bc2970`(`datacenter_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_83a0eb3f`(`profile_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_60c2c5fffcb40895_idx`(`owner_id`, `identifier`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4b76dd7c4564df4f_idx`(`ownergroup_id`, `identifier`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_47ecdfd54025f1f1_idx`(`owner_id`, `createTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_59016f4a7ffbcaaa_idx`(`owner_id`, `updateTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_5b203a171bdbab38_idx`(`owner_id`, `status`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_3e88a7c1b2b5c693_idx`(`owner_id`, `exported`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_58dfc6401ef0e359_idx`(`owner_id`, `crossrefStatus`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_431b22d7016b97df_idx`(`owner_id`, `profile_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_52f3896c5fc67016_idx`(`owner_id`, `isTest`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_5c11adaf88d856d0_idx`(`owner_id`, `searchablePublicationYear`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_54da573427e72c0e_idx`(`owner_id`, `searchableResourceType`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_18a46334256a7530_idx`(`owner_id`, `hasMetadata`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_1d05153b51fd9dff_idx`(`owner_id`, `hasIssues`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_76e131b0c70070a1_idx`(`owner_id`, `resourceCreatorPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_198f8d3796dae4b9_idx`(`owner_id`, `resourceTitlePrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_owner_id_263dc1dd7d2fd3ef_idx`(`owner_id`, `resourcePublisherPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_39b7cdc64bc267c3_idx`(`ownergroup_id`, `createTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_6c5194bcf1d0014e_idx`(`ownergroup_id`, `updateTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_1d431d7513ab02ec_idx`(`ownergroup_id`, `status`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_48b886662536e7fd_idx`(`ownergroup_id`, `exported`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_2114f948ed092669_idx`(`ownergroup_id`, `crossrefStatus`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_6cfbff68ca3e25cb_idx`(`ownergroup_id`, `profile_id`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_449f25bec77c57da_idx`(`ownergroup_id`, `isTest`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4a1baf4823ddab6c_idx`(`ownergroup_id`, `searchablePublicationYear`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_54e4e22002a54d2_idx`(`ownergroup_id`, `searchableResourceType`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_65871830cd29aaf0_idx`(`ownergroup_id`, `hasMetadata`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_4ad29fb0ede49103_idx`(`ownergroup_id`, `hasIssues`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_3ac1ed25c2bfbb2d_idx`(`ownergroup_id`, `resourceCreatorPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_68875bac9225d3c9_idx`(`ownergroup_id`, `resourceTitlePrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_ownergroup_id_2388bfe261a735c5_idx`(`ownergroup_id`, `resourcePublisherPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_58de9f6f00b8058e_idx`(`publicSearchVisible`, `identifier`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_1932465b0335635c_idx`(`publicSearchVisible`, `createTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_47b0a294295f5ef5_idx`(`publicSearchVisible`, `updateTime`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_1e447c57e83c8d5d_idx`(`publicSearchVisible`, `searchablePublicationYear`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_47396846c619370f_idx`(`publicSearchVisible`, `searchableResourceType`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_117042133b78a88e_idx`(`publicSearchVisible`, `resourceCreatorPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_publicSearchVisible_6807647c6d8cb52_idx`(`publicSearchVisible`, `resourceTitlePrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifie_publicSearchVisible_2e067bd0a9494a38_idx`(`publicSearchVisible`, `resourcePublisherPrefix`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_searchableTarget_24d34538786996df_idx`(`searchableTarget`)
;
alter table ezidapp_searchidentifier
add key `ezidapp_searchidentifier_oaiVisible_1d291a23fcff2ce2_idx`(`oaiVisible`, `updateTime`)
;

alter table ezidapp_searchidentifier
add fulltext key `ezidapp_searchidentifier_resourceTitle`(`resourceTitle`)
;
alter table ezidapp_searchidentifier
add fulltext key `ezidapp_searchidentifier_resourceCreator`(`resourceCreator`)
;
alter table ezidapp_searchidentifier
add fulltext key `ezidapp_searchidentifier_resourcePublisher`(`resourcePublisher`)
;
alter table ezidapp_searchidentifier
add fulltext key `ezidapp_searchidentifier_keywords`(`keywords`)
;
