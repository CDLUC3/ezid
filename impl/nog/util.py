import logging
import logging.config
import sys


def log_to_console(module_name, is_debug):
    """Add a logging handler that writes to the console and configure logging
    levels.

    Args:
        is_debug: Enable debug level logging.
        module_name: __name_ from caller.

        If debug level logging IS enabled, we just set the root logger to DEBUG so that
        we can log at all levels without getting filtered. We leave the rest of the tree
        alone, which allows levels to stay as configured in the Django / EZID settings
        (which again is based on the DEBUG settings).

        If debug level logging is NOT enabled, we want to be able to log at all levels
        above DEBUG and have those not be filtered out. So we set the root logger to
        INFO. But we don't want to see INFO level from from other loggers, so we bump
        all existing loggers to ERROR.
    """
    root_logger = logging.getLogger()
    # Remove any existing handlers that write to the console (stdout or stderr).
    while True:
        for h in root_logger.handlers:
            if isinstance(h, logging.StreamHandler):
                if h.stream in (sys.stdout, sys.stderr):
                    print(('Removing handler: {}'.format(h.level)))
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
    formatter = logging.Formatter('%(levelname)-8s %(module)s - %(message)s')
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
