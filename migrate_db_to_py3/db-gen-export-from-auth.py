#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

"""Generate export shell scripts"""

import logging
import pathlib
import sys

import toml

HERE_PATH = pathlib.Path(__file__).parent.resolve()


log = logging.getLogger(__name__)


S = r"""
# {host} 

e() {{
  printf '%s = %s\n' "$1" "$2"
  export "$1"="$2"
}}

e DB_HOST '{db}'
e DB_PORT '{port}'
e DB_USER '{user}'
e DB_PW   '{pw}'
e DB_NAME '{name}'
"""


def main():
    d = toml.load((HERE_PATH / '___db_auth.toml').open())

    for host, dd in d['servers'].items():
        print('-' * 80)
        s = S.format(
            host=host,
            db=dd['db'],
            port=dd['port'],
            user='eziddba',
            pw=dd['user']['eziddba']['pw'],
            name=dd['name'],
        )
        print(s)
        pathlib.Path(f'___export_{host}_db_env.sh').write_text(s)


if __name__ == '__main__':
    sys.exit(main())
