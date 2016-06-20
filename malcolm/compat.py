try:
    from queue import Queue # noqa
except ImportError:
    from Queue import Queue # noqa

try:
    base_string = basestring
except NameError:
    base_string = str
