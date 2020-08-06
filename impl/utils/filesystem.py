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


@contextlib.contextmanager
def temp_file_for_obj(o, ext_str=None, to_utf_8=False, keep_file=False, lf=False):
    """Context manager that provides `o` as a path. If object is the path to a valid
    file, the file is used directly. If `o` is ``bytes`` or ``str``, it is written to a
    temporary file. If `o` is ``str``, it is written as UTF-8 ``bytes``.

    Args:
        o (:obj:`str`, :obj:`bytes`, :obj:`path` or :obj:`Path`): Object for which to
        return a path.
        ext_str (str): Filename extension to use when creating temporary files.
          Ignored if no file is created. This is to provide file type information to
          utilities that will read the file. Includes the period. E.g., ``.xml``.
        to_utf_8: Force file encoding to UTF-8 by replacing any byte sequences that are
        not valid UTF-8 with the Unicode replacement character "?".
        keep_file (bool):
            True: Do not delete the temporary file when exiting the context. The file
                must be deleted manually.
        lf (bool):
            True: Add a linefeed to the end of the file if one is not already there.
    Returns:
        pathlib.Path: The path to a file for `o`.
    """
    if isinstance(o, pathlib.Path):
        if not o.exists():
            raise Exception("File does not exist: {}".format(o))
        yield o.absolute()
        return

    if safe_path_exists(o):
        yield pathlib.Path(o).absolute()
        return

    if isinstance(o, str):
        o = o.encode("utf-8")

    if to_utf_8:
        o = o.decode('utf-8', errors="replace")
        o = o.encode("utf-8", errors="replace")

    with tempfile.NamedTemporaryFile(
        suffix=ext_str or ".tmp", delete=not keep_file
    ) as tmp_file:
        tmp_file.write(o)
        if lf and not o.endswith(b'\n'):
            tmp_file.write(b'\n')
        tmp_file.seek(0)
        yield pathlib.Path(tmp_file.name).absolute()


def safe_path_exists(o):
    """Check if `o` is a path to an existing file.

    ``pathlib.Path(o).is_file()`` and ``os.path.exists()`` raise various types of
    exceptions if unable to convert `o` to a value suitable for use as a path. This
    method aims to allow checking any object without raising exceptions.

    Args:
        o (object): An object that may be a path.

    Returns:
        bool: True if `o` is a path.
    """
    try:
        if isinstance(o, pathlib.Path):
            return o.is_file()
        if not isinstance(o, (str, bytes)):
            return False
        if len(o) > 1024:
            return False
        if isinstance(o, bytes):
            o = o.decode("utf-8")
        return pathlib.Path(o).is_file()
    except Exception:
        pass
    return False
