class MinterError(Exception):
    pass

class MinterNotSpecified(MinterError):
    """No minter is specified for shoulder"""
    pass

