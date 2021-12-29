#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Entry point for all Django and EZID management commands

Do not set a default for DJANGO_SETTINGS_MODULE here, as it tends to hide a missing
configuration, and no single default is good for all environments.
"""
import sys

import django.core.management


def main():
    django.core.management.execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
