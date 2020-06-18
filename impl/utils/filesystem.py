import errno
import os
import sys


def mkdir_p(file_path):
    """Create any missing directories leading up to the file specified by {file_path}.

    Note that {file_path} is assumed to be a file path, so the last element in the path
    is ignored.
    """
    dir_path = os.path.dirname(file_path)
    try:
        os.makedirs(dir_path)
    except OSError as e:
        if not (e.errno == errno.EEXIST and os.path.isdir(dir_path)):
            raise


def abs_path(rel_path):
    """Resolve {rel_path} relative to the dir in which the module of the caller is
    located.

    E.g., calling filesystem.abs_path('..') from /a/b/c.py returns /a.
    """
    return os.path.abspath(
        # os.path.join(os.path.dirname(__file__), rel_path)
        # This returns the path of the pytest assertion, not this file
        os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), rel_path)
    )

