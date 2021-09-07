#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.test_settings')

import django.core.management


def main():
    django.core.management.execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
