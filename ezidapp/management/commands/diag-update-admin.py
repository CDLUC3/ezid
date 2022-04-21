#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

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
import argparse
import datetime

import django.conf
import django.contrib.auth
import django.contrib.auth.models
import django.core.management
import django.db.transaction

import ezidapp.models.group
import ezidapp.models.realm
import ezidapp.models.user

NOW_TS = datetime.datetime.now()

SETTINGS_DICT = {
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
        'username': django.conf.settings.ADMIN_USERNAME,
        'password': django.conf.settings.ADMIN_PASSWORD,
    },
    # EZID custom user authentication
    'realm': {
        "name": django.conf.settings.ADMIN_REALM,
    },
    'group': {
        'accountType': '',
        'agreementOnFile': False,
        'crossrefEnabled': django.conf.settings.ADMIN_CROSSREF_ENABLED,
        'groupname': django.conf.settings.ADMIN_GROUPNAME,
        'notes': django.conf.settings.ADMIN_NOTES,
        'organizationAcronym': django.conf.settings.ADMIN_ORG_ACRONYM,
        'organizationName': django.conf.settings.ADMIN_ORG_NAME,
        'organizationStreetAddress': '(:unap)',
        'organizationUrl': django.conf.settings.ADMIN_ORG_URL,
        'pid': django.conf.settings.ADMIN_GROUP_PID,
    },
    'user': {
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
        'pid': django.conf.settings.ADMIN_USER_PID,
        'primaryContactEmail': django.conf.settings.ADMIN_PRIMARY_CONTACT_EMAIL,
        'primaryContactName': django.conf.settings.ADMIN_PRIMARY_CONTACT_NAME,
        'primaryContactPhone': django.conf.settings.ADMIN_PRIMARY_CONTACT_PHONE,
        'secondaryContactEmail': django.conf.settings.ADMIN_SECONDARY_CONTACT_EMAIL,
        'secondaryContactName': django.conf.settings.ADMIN_SECONDARY_CONTACT_NAME,
        'secondaryContactPhone': django.conf.settings.ADMIN_SECONDARY_CONTACT_PHONE,
        'username': django.conf.settings.ADMIN_USERNAME,
    },
}


class Command(django.core.management.BaseCommand):
    help = "Create or update the EZID admin account, password and related details"

    def create_parser(self, *args, **kwargs):
        parser = super(Command, self).create_parser(*args, **kwargs)
        parser.formatter_class = argparse.RawTextHelpFormatter
        return parser

    def handle(self, *args, **options):
        # Django auth

        # https://docs.djangoproject.com/en/3.2/topics/auth/customizing/
        user_model = django.contrib.auth.get_user_model()

        with django.db.transaction.atomic():
            if not user_model.objects.filter(username=django.conf.settings.ADMIN_USERNAME).exists():
                user_model.objects.create_superuser(**SETTINGS_DICT['auth.user'])

        user = user_model.objects.get(
            username=django.conf.settings.ADMIN_USERNAME,
        )
        user.set_password(django.conf.settings.ADMIN_PASSWORD)
        user.save()

        # EZID custom auth

        realm, _created = ezidapp.models.realm.Realm.objects.update_or_create(
            name=SETTINGS_DICT['realm']['name'],
            defaults=SETTINGS_DICT['realm'],
        )

        group, _created = ezidapp.models.group.Group.objects.update_or_create(
            pid=django.conf.settings.ADMIN_GROUP_PID,
            defaults={
                **SETTINGS_DICT['group'],
                'realm': realm,
            },
        )

        user, _created = ezidapp.models.user.User.objects.update_or_create(
            pid=django.conf.settings.ADMIN_USER_PID,
            defaults={
                **SETTINGS_DICT['user'],
                'realm': realm,
                'group': group,
            },
        )
        user.setPassword(django.conf.settings.ADMIN_PASSWORD)
        user.save()
