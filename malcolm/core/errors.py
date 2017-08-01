class MalcolmException(Exception):
    """Base class for all Malcolm exceptions"""
    pass


class TimeoutError(MalcolmException):
    """The operation exceeded the given deadline"""
    pass


class AbortedError(MalcolmException):
    """The operation was aborted"""
    pass


class ResponseError(MalcolmException):
    """A Put or Post raised an Error"""
    pass


class UnexpectedError(MalcolmException):
    """We received an object we weren't expecting"""
    pass


class BadValueError(MalcolmException):
    """match_update() received one of the specified bad values"""
    pass


class WrongThreadError(MalcolmException):
    """When you have called something outside of cothread's thread"""
    pass


class YamlError(MalcolmException):
    """When instantiating some YAML raises an error"""
    pass