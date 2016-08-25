try:
    # python 2
    import Queue as queue  # noqa
except ImportError:
    # python 3
    import queue  # noqa

try:
    # python 2
    str_ = basestring
except NameError:
    # python 3
    str_ = str

try:
    # python 2
    long_ = long  # pylint:disable=invalid-name
except NameError:
    # python 3
    long_ = int  # pylint:disable=invalid-name
