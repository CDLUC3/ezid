#!/usr/bin/env python

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.settings')

import django.core.management


def main():
    django.core.management.execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
