#  Copyright©2021, Regents of the University of California
#  http://creativecommons.org/licenses/BSD

class MinterError(Exception):
    pass


class MinterNotSpecified(MinterError):
    """No minter is specified for shoulder."""

    pass


class MinterPathError(MinterError):
    def __init__(self, msg, path, ns):
        super(MinterPathError, self).__init__(
            '{}. path="{}", ns="{}"'.format(
                msg, path.as_posix() if path else None, str(ns)
            )
        )
