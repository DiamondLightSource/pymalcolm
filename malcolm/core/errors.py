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


class YamlError(MalcolmException):
    """When instantiating some YAML raises an error"""
    pass


class FieldError(MalcolmException):
    """Basically a KeyError but without quotation marks in error message"""
    pass


class NotWriteableError(MalcolmException):
    """The field is not currently writeable, so cannot Put or Post to it"""

