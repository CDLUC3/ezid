"""Create or update the EZID admin account, password and related details

If the EZID admin account does not already exist, crate it. Then, both for existing and
newly created account, set the EZID admin password and related details as configured in
the `ADMIN_` settings in `settings.py`.

This command must be run in order to apply any changes made to the `ADMIN_` settings.

Notes:

'admin' is the only user that is authenticated using Django's standard authorization,
and so is the only user in Django's `auth_user` table.

EZID uses custom authentication for regular users, which combines authentication and
storage of user account information. As the 'admin' account also stores account
information in a user account, the admin user is created both as a Django superuser for
Django and as a user flagged with elevated access in EZID's custom authentication system
"""

import datetime

import django.conf
import django.contrib.auth
import django.contrib.auth.models
import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.search_group
import ezidapp.models.search_realm
import ezidapp.models.search_user
import ezidapp.models.store_group
import ezidapp.models.store_realm
import ezidapp.models.store_user

NOW_TS = datetime.datetime.now()

ADMIN_MODEL_DICT = {
    # Django standard user authentication
    'auth.user': {
        'date_joined': NOW_TS,
        'email': django.conf.settings.ADMIN_EMAIL,
        'first_name': django.conf.settings.ADMIN_DISPLAY_NAME,
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
        'last_login': NOW_TS,
        'last_name': '',
        # 'username': django.conf.settings.ADMIN_USERNAME,
        'password': django.conf.settings.ADMIN_PASSWORD,
    },
    'contenttypes.contenttype': {
        'app_label': 'admin',
        'model': 'logentry',
    },
    # EZID custom user authentication
    'ezidapp.StoreRealm': {
        "name": django.conf.settings.ADMIN_STORE_REALM,
    },
    'ezidapp.SearchRealm': {
        "name": django.conf.settings.ADMIN_SEARCH_REALM,
    },
    'ezidapp.storeuser': {
        'accountEmail': django.conf.settings.ADMIN_EMAIL,
        'crossrefEmail': django.conf.settings.ADMIN_CROSSREF_EMAIL,
        'crossrefEnabled': django.conf.settings.ADMIN_CROSSREF_ENABLED,
        'displayName': django.conf.settings.ADMIN_DISPLAY_NAME,
        'inheritGroupShoulders': False,
        'isGroupAdministrator': False,
        'isRealmAdministrator': False,
        'isSuperuser': True,
        'loginEnabled': True,
        'notes': django.conf.settings.ADMIN_NOTES,
        # 'password': django.conf.settings.ADMIN_PASSWORD,
        'pid': django.conf.settings.ADMIN_STORE_USER_PID,
        'primaryContactEmail': django.conf.settings.ADMIN_PRIMARY_CONTACT_EMAIL,
        'primaryContactName': django.conf.settings.ADMIN_PRIMARY_CONTACT_NAME,
        'primaryContactPhone': django.conf.settings.ADMIN_PRIMARY_CONTACT_PHONE,
        'secondaryContactEmail': django.conf.settings.ADMIN_SECONDARY_CONTACT_EMAIL,
        'secondaryContactName': django.conf.settings.ADMIN_SECONDARY_CONTACT_NAME,
        'secondaryContactPhone': django.conf.settings.ADMIN_SECONDARY_CONTACT_PHONE,
        'username': django.conf.settings.ADMIN_USERNAME,
    },
    'ezidapp.storegroup': {
        'accountType': '',
        'agreementOnFile': False,
        'crossrefEnabled': django.conf.settings.ADMIN_CROSSREF_ENABLED,
        'groupname': django.conf.settings.ADMIN_GROUPNAME,
        'notes': django.conf.settings.ADMIN_NOTES,
        'organizationAcronym': django.conf.settings.ADMIN_ORG_ACRONYM,
        'organizationName': django.conf.settings.ADMIN_ORG_NAME,
        'organizationStreetAddress': '(:unap)',
        'organizationUrl': django.conf.settings.ADMIN_ORG_URL,
        'pid': django.conf.settings.ADMIN_STORE_GROUP_PID,
    },
    'ezidapp.searchuser': {
        'pid': django.conf.settings.ADMIN_SEARCH_USER_PID,
        'username': django.conf.settings.ADMIN_USERNAME,
    },
    'ezidapp.searchgroup': {
        'groupname': django.conf.settings.ADMIN_GROUPNAME,
        'pid': django.conf.settings.ADMIN_SEARCH_GROUP_PID,
    },
}


class Command(django.core.management.BaseCommand):
    help = "Create or update the EZID admin account, password and related details"

    def handle(self, *args, **options):
        # Django auth

        # https://docs.djangoproject.com/en/3.2/topics/auth/customizing/
        user_model = django.contrib.auth.get_user_model()

        with django.db.transaction.atomic():
            if not user_model.objects.filter(
                username=django.conf.settings.ADMIN_USERNAME
            ).exists():
                user_model.objects.create_superuser(
                    **ADMIN_MODEL_DICT['auth.user'],username=django.conf.settings.ADMIN_USERNAME
                )

        user = user_model.objects.get(username=django.conf.settings.ADMIN_USERNAME)
        user.set_password(django.conf.settings.ADMIN_PASSWORD)
        user.save()

        # EZID custom auth

        # Store
        store_realm = ezidapp.models.store_realm.StoreRealm.objects.update_or_create(
            defaults=ADMIN_MODEL_DICT['ezidapp.StoreRealm'], name='CDL'
        )[0]
        store_group = ezidapp.models.store_group.StoreGroup.objects.update_or_create(
            defaults={
                **ADMIN_MODEL_DICT['ezidapp.storegroup'],
                # **{
                'realm': store_realm,
                'groupname': django.conf.settings.ADMIN_GROUPNAME,
                # },
            },
            groupname=django.conf.settings.ADMIN_GROUPNAME,
        )[0]
        store_user = ezidapp.models.store_user.StoreUser.objects.update_or_create(
            defaults={
                **ADMIN_MODEL_DICT['ezidapp.storeuser'],
                'realm': store_realm,
                'group': store_group,
                'username': django.conf.settings.ADMIN_USERNAME,
            },
            username='admin',
        )[0]
        store_user.setPassword(django.conf.settings.ADMIN_PASSWORD)
        store_user.save()

        # Search
        search_realm = ezidapp.models.search_realm.SearchRealm.objects.update_or_create(
            defaults=ADMIN_MODEL_DICT['ezidapp.SearchRealm'],
            name='CDL',
        )[0]
        search_group = ezidapp.models.search_group.SearchGroup.objects.update_or_create(
            defaults={
                **ADMIN_MODEL_DICT['ezidapp.searchgroup'],
                'realm': search_realm,
                'groupname': 'admin',
                # },
            },
            groupname='admin',
        )[0]
        search_user = ezidapp.models.search_user.SearchUser.objects.update_or_create(
            defaults={
                **ADMIN_MODEL_DICT['ezidapp.searchuser'],
                'realm': search_realm,
                'group': search_group,
                'username': 'admin',
                # },
            },
            username='admin',
        )[0]
        # search_user.setPassword(django.conf.settings.ADMIN_PASSWORD)
        # search_user.save()
