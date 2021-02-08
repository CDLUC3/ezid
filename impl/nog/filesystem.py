import contextlib
import os
import pathlib
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import urllib.response

FILENAME_SAFE_CHARS = " @$,~*&"


def get_safe_reversible_path(*path_list):
    """Escape characters that are not allowed or often cause issues when used
    in file- or directory names, then join the arguments to a filesystem path.

    This generates a string that is reversible but may not be easy to read.

    Args:
        *path_list:

    Returns:
        (:obj:`str` or :obj:`Path`): A path safe for use as a as a file- or directory name.

    See Also:
        If a reversible path is not required, see :func:`get_safe_lossy_path`, which is
        not reversible, but may be easier to read.

        To get get the original string from the path, see :func:`get_original_path`.
    """
    return os.path.join(*[get_safe_reversible_path_element(p) for p in path_list])


def get_safe_reversible_path_element(s):
    """Replace characters that are not allowed, have special semantics, or may
    cause security issues, when used in file- or directory names, with
    filesystem safe reversible codes.

     On Unix, names starting with period are usually hidden in the filesystem. We don't
     want there to be a chance of generating hidden files by using this function. But
     we also don't want to escape dots in general since that makes the filenames much
     harder to read. So we escape the dot only when it's at the start of the string.

    Args:
         s (str): Any Unicode string

     Returns:
         str: A string safe for use as a file- or directory name.
    """
    out_str = urllib.parse.quote(s.encode("utf-8"), safe=FILENAME_SAFE_CHARS)
    if out_str.startswith('.'):
        out_str = '%2e{}'.format(out_str[1:])
    return out_str


def create_missing_directories_for_file(file_path):
    """Create any missing directories leading up to the file specified by
    {file_path}.

    Note that {file_path} is assumed to be a file path, so the last element in the path
    is ignored.

    Args:
        file_path (str): Relative or absolute path to a file that may or may not exist.

            Must be a file path, as any directory element at the end of the path will
              not be created.

    See Also:
        create_missing_directories_for_dir()
    """
    create_missing_directories_for_dir(pathlib.Path(file_path).parent)


def create_missing_directories_for_dir(dir_path):
    """Create any directories in ``dir_path`` that do not yet exist.

    Args:
        dir_path (str): Relative or absolute path to a directory that may or may not
          exist.

            Must be a directory path, as any filename element at the end of the path
              will also be created as a directory.

    See Also:
        create_missing_directories_for_file()
    """
    dir_path = pathlib.Path(dir_path)
    if dir_path.exists():
        if not dir_path.is_dir():
            raise IOError(
                "Path already exists but is not a directory: {}".format(
                    dir_path.as_posix()
                )
            )
    else:
        pathlib.Path(dir_path).mkdir(parents=True)


def abs_path_from_base(base_path, rel_path):
    """Join a base and a relative path and return an absolute path to the
    resulting location.

    Args:
        base_path (str): Relative or absolute path to prepend to ``rel_path``.
        rel_path (str): Path relative to the location of the module file from which this
          function is called.

    Returns:
        (:obj:`str` or :obj:`Path`): Absolute path to the location specified by ``rel_path``.
    """
    # noinspection PyProtectedMember
    return os.path.abspath(
        os.path.join(
            os.path.dirname(sys._getframe(1).f_code.co_filename), base_path, rel_path
        )
    )


def abs_path(rel_path):
    """Convert a path that is relative to the module from which this function
    is called, to an absolute path.

    E.g., calling abs_path('..') from /a/b/c.py returns /a.

    Args:
        rel_path (str): Path relative to the location of the module file from which this
          function is called.

    Returns:
        (:obj:`str` or :obj:`Path`): Absolute path to the location specified by ``rel_path``.
    """
    # noinspection PyProtectedMember
    return os.path.abspath(
        os.path.join(os.path.dirname(sys._getframe(1).f_code.co_filename), rel_path)
    )


@contextlib.contextmanager
def temp_file_for_obj(o, ext_str=None, to_utf_8=False, keep_file=False, lf=False):
    """Context manager that provides `o` as a path. If object is the path to a
    valid file, the file is used directly. If `o` is ``bytes`` or ``str``, it
    is written to a temporary file. If `o` is ``str``, it is written as UTF-8
    ``bytes``.

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
