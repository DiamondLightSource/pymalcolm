class Error(Exception):
    """Base class for all Malcolm exceptions"""
    pass


class TimeoutError(Error):
    """The operation exceeded the given deadline"""
    pass


class AbortedError(Error):
    """The operation was aborted"""
    pass


class ResponseError(Error):
    """A Put or Post raised an Error"""
    pass


class UnexpectedError(Error):
    """We received an object we weren't expecting"""
    pass


class BadValueError(Error):
    """match_update() received one of the specified bad values"""
    pass
