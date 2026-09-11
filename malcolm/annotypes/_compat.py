import inspect
import sys


# Taken from six
def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


def getargspec(f):
    if sys.version_info < (3,):
        args, varargs, keywords, defaults = inspect.getargspec(f)
    else:
        # Need to use fullargspec in case there are annotations
        args, varargs, keywords, defaults = inspect.getfullargspec(f)[:4]
    return inspect.ArgSpec(args, varargs, keywords, defaults)


def func_globals(f):
    if sys.version_info < (3,):
        return f.func_globals
    else:
        return f.__globals__


if sys.version_info < (3,):
    # python 2
    str_ = basestring
else:
    # python 3
    str_ = str