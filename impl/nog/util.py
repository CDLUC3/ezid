#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

import logging
import logging.config
import sys

log = logging.getLogger(__name__)


def log_setup(module_name, is_debug, suppress_context=False):
    """Add a logging handler that writes to the console and configure logging
    levels.

    Args:
        is_debug: Enable debug level logging.
        module_name: __name_ from caller.
        suppress_context ():

        If debug level logging IS enabled, we just set the root logger to DEBUG so that
        we can log at all levels without getting filtered. We leave the rest of the tree
        alone, which allows levels to stay as configured in the Django / EZID settings
        (which again is based on the DEBUG settings).

        If debug level logging is NOT enabled, we want to be able to log at all levels
        above DEBUG and have those not be filtered out. So we set the root logger to
        INFO. But we don't want to see INFO level from other loggers, so we bump all
        existing loggers to ERROR.
    """
    root_logger = logging.getLogger()
    # Remove any existing handlers that write to the console (stdout or stderr).
    while True:
        for h in root_logger.handlers:
            if isinstance(h, logging.StreamHandler):
                if h.stream in (sys.stdout, sys.stderr):
                    # print('Removing handler: {}'.format(h.level))
                    root_logger.removeHandler(h)
                    break
        else:
            break

    # Adjust the logging levels of existing loggers
    if is_debug:
        print('Setting up logging to console')
    else:
        for logger_name in list(logging.root.manager.loggerDict):
            logging.getLogger(logger_name).setLevel(logging.ERROR)
    for n in ('impl.nog.reload', 'impl.nog.shoulder'):
        logging.getLogger(n).setLevel(logging.DEBUG if is_debug else logging.INFO)

    # Add new handlers
    if suppress_context:
        format_str = '%(levelname)-8s %(message)s'
    else:
        format_str = '%(name)s %(levelname)-8s %(module)s - %(message)s'
        if is_debug:
            format_str = '%(filename)s:%(lineno)d %(module)s ' + format_str

    formatter = logging.Formatter(format_str)
    base_level = logging.DEBUG if is_debug else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(base_level)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(base_level)

    # Ensure that log records from the logger at __name__ will propagate to the root.
    mod_path = []
    for mod_str in module_name.split('.'):
        mod_path.append(mod_str)
        logging.getLogger('.'.join(mod_path)).setLevel(base_level)

    if is_debug:
        log = logging.getLogger(__name__)
        log.debug('logging: DEBUG level logging enabled')
        log.info('logging: INFO level logging enabled')
        log.error('logging: ERROR level logging enabled')

    # import logging_tree
    # print(logging_tree.printout())


def print_table(row_list, out_fn=log.info):
    """Print a list of rows as a table with columns adjusted to the longest string in each column"""
    rot_list = list(zip(*row_list[::-1]))
    max_list = [max(len(str(s)) for s in r) for r in rot_list]
    fmt_str = ' '.join([f'{{:<{max(len(str(s)) for s in r)}}}' for r in rot_list])
    [out_fn(fmt_str.format(*r)) for r in row_list]
