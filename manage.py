#!/usr/bin/env python

import sys
import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings.settings'

import django.core.management


def main():
    django.core.management.execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
