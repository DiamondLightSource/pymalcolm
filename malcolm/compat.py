try:
    # python 2
    import Queue as queue  # noqa
except ImportError:
    # python 3
    import queue  # noqa

try:
    # python 2
    base_string = basestring
except NameError:
    # python 3
    base_string = str
