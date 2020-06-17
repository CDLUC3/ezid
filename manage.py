#!/usr/bin/env python

import os
import sys

import django.core.management


def main():
    sys.path.append(_abs_path(".."))
    sys.path.append(_abs_path("."))
    sys.path.append(_abs_path("impl"))
    sys.path = sorted(set(sys.path), key=lambda x: (0, x) if "/ezid" in x else (1, x))

    # print('syspath:\n' + '\n'.join(sys.path))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings.localdev")
    django.core.management.execute_from_command_line(sys.argv)


def _abs_path(rel_path):
    return os.path.abspath(
        os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), rel_path)
    )


if __name__ == "__main__":
    main()
