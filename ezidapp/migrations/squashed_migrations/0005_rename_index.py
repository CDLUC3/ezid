# Generated by Django 4.2.11 on 2024-04-22 16:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ezidapp', '0004_minter'),
    ]

    operations = [
        migrations.RenameIndex(
            model_name='linkchecker',
            new_name='ezidapp_lin_owner_i_866e15_idx',
            old_fields=('owner_id', 'isBad', 'lastCheckTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_c3cf9a_idx',
            old_fields=('ownergroup_id', 'searchablePublicationYear'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_f5f078_idx',
            old_fields=('owner_id', 'resourceCreatorPrefix'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_e25844_idx',
            old_fields=('owner_id', 'identifier'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_155d5f_idx',
            old_fields=('owner_id', 'resourceTitlePrefix'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_89f1d2_idx',
            old_fields=('ownergroup_id', 'identifier'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_b09cbd_idx',
            old_fields=('owner_id', 'createTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_1c8373_idx',
            old_fields=('owner_id', 'hasIssues'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_f36098_idx',
            old_fields=('owner_id', 'searchableResourceType'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_b5c787_idx',
            old_fields=('ownergroup_id', 'resourceTitlePrefix'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_publicS_76c2e5_idx',
            old_fields=('publicSearchVisible', 'identifier'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_c4d7aa_idx',
            old_fields=('owner_id', 'hasMetadata'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_publicS_44eb10_idx',
            old_fields=('publicSearchVisible', 'createTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_845796_idx',
            old_fields=('owner_id', 'exported'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_3808dc_idx',
            old_fields=('ownergroup_id', 'exported'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_940df1_idx',
            old_fields=('owner_id', 'updateTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_oaiVisi_95a198_idx',
            old_fields=('oaiVisible', 'updateTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_a9c320_idx',
            old_fields=('owner_id', 'status'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_36ea7c_idx',
            old_fields=('ownergroup_id', 'isTest'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_df06b0_idx',
            old_fields=('ownergroup_id', 'createTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_publicS_a5777f_idx',
            old_fields=('publicSearchVisible', 'searchableResourceType'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_04c9f2_idx',
            old_fields=('ownergroup_id', 'hasIssues'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_59a541_idx',
            old_fields=('owner_id', 'profile_id'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_19a761_idx',
            old_fields=('ownergroup_id', 'updateTime'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_165cbb_idx',
            old_fields=('ownergroup_id', 'profile_id'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_cfdb17_idx',
            old_fields=('owner_id', 'crossrefStatus'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_owner_i_f854de_idx',
            old_fields=('owner_id', 'searchablePublicationYear'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_ownergr_de548b_idx',
            old_fields=('ownergroup_id', 'crossrefStatus'),
        ),
        migrations.RenameIndex(
            model_name='searchidentifier',
            new_name='ezidapp_sea_publicS_edadba_idx',
            old_fields=('publicSearchVisible', 'searchablePublicationYear'),
        ),
    ]
