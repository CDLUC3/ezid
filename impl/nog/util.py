import logging
import sys


def add_console_handler(is_debug):
    """Add a logging handler that writes to the console."""
    log_format = logging.Formatter('%(levelname)-8s %(module)s - %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG if is_debug else logging.INFO)
    handler.setFormatter(log_format)
    logging.getLogger('').addHandler(handler)
    logging.getLogger('').setLevel(logging.DEBUG if is_debug else logging.INFO)
