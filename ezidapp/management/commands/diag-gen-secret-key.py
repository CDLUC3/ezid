#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Print a random string that can be used in the settings.SECRET_KEY setting.
"""
import logging

import django.core.management.utils

log = logging.getLogger(__name__)


class Command(django.core.management.BaseCommand):
    help = __doc__

    def handle(self, *_, **opt):
        print(django.core.management.utils.get_random_secret_key())
        print('\nNote: Must be copied into settings.SECRET_KEY manually')
