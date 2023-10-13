#!/usr/bin/env python

#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import argparse
import contextlib
import fileinput
import logging
import re
import sys

import impl.nog_sql.counter

log = logging.getLogger(__name__)


def main():
    # noinspection PyTypeChecker
    parser = argparse.ArgumentParser(
        prog='TagLog',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
    )
    parser.add_argument(
        'log_list',
        metavar='LOGFILE',
        nargs='*',
        help='EZID log files',
    )
    parser.add_argument(
        '--shoulder',
        metavar='ARK/DOI',
        dest='shoulder_str',
        help=(
            'Shoulder of identifiers to highlight. '
            'If provided, other identifiers are suppressed (replaced with "...")'
        ),
    )
    parser.add_argument(
        '--debug',
        '-v',
        action='store_true',
        help='Enable debug level logging',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(levelname)-8s %(message)s',
        stream=sys.stderr,
    )

    try:
        with TagLog(args) as tag_log:
            tag_log.tag()
    except Exception as e:
        print(repr(e))
        raise

    log.info('Completed')


class TagLog:
    def __init__(self, args):
        self.args = args
        self.rx_dict = dict(
            uuid=dict(
                rx=re.compile(r'([0-9a-fA-F]{32})'),
                id_dict={},
            ),
            ark=dict(
                rx=re.compile(
                    r'((ark(?::/))([0-9bcdfghjkmnpqrstvwxz]\\d{3,4})(?:(/)([0-9a-z./]*)))'
                ),
                id_dict={},
            ),
            doi=dict(
                rx=re.compile(
                    r'((?:(doi)(?::10.))(\\d{4,5})(?:(/)([0-9A-Z./]*))?)',
                ),
                id_dict={},
            ),
        )
        self.exit_stack = None

    def __enter__(self):
        self.exit_stack = contextlib.ExitStack()
        self.counter = self.exit_stack.enter_context(impl.nog_sql.counter.Counter())
        self.count = self.counter.count
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit_stack.close()
        self.write_id_ref()

    def write_id_ref(self):
        """Append a map of tag ID to real identifier to end of tagged log."""
        print('-' * 100)
        for type_str, type_dict in list(self.rx_dict.items()):
            for id_str, instance_dict in list(type_dict['id_dict'].items()):
                s = '{} ID={} C={}'.format(
                    type_str, instance_dict['tag_id'], instance_dict['acc_count']
                )
                print(f'{s}: {id_str}')

    def tag(self):
        line_no = 0

        for line_str in fileinput.input(self.args.log_list):
            line_str = line_str.strip()

            # print('\nORIG {:>08} {}'.format(line_no, line_str))

            self.count(line_str, '_ Log lines processed')
            line_str = line_str.strip()

            new_str = ''
            pos = 0

            for type_str, type_dict in list(self.rx_dict.items()):

                for m in type_dict['rx'].finditer(line_str):
                    id_dict = type_dict['id_dict']
                    id_str = m.group(1)

                    # print('>>>  {:>8} {}'.format('', id_str))

                    if (
                        self.args.shoulder_str is None
                        or id_str.startswith(self.args.shoulder_str)
                        or type_str == 'UUID'
                    ):
                        if id_str not in id_dict:
                            instance_dict = id_dict[id_str] = dict(
                                tag_id=len(id_dict), acc_count=1
                            )
                        else:
                            instance_dict = id_dict[id_str]
                            instance_dict['acc_count'] += 1

                        s1 = ' ### ID={} C={} ### '.format(
                            instance_dict['tag_id'], instance_dict['acc_count']
                        )
                        s = s1

                    else:
                        s = '...'

                    # Add the tag after the identifier (leaves the original identifier in place)
                    end_pos = m.end(1)
                    # # Replace the original identifier with the tag
                    # end_pos = m.start(1)

                    new_str += line_str[pos:end_pos] + s
                    pos = m.end(1)

                    self.count(line_str, f'{type_str.upper()} found')

            new_str += line_str[pos:]

            print('{:>8} {}'.format(line_no, new_str))
            line_no += 1

    def log_db_counts(self):
        [log.info(f'{k}: {len(d)} strings') for k, d in list(self.rx_dict.items())]


class TagLogError(Exception):
    pass


if __name__ == '__main__':
    sys.exit(main())
