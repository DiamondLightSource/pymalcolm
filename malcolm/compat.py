import os
import sys
from xml.etree import cElementTree as ET

try:
    # ruamel exists, use this OrderedDict as it is faster
    from ruamel.ordereddict import ordereddict as OrderedDict
except ImportError:
    # Fallback to slower collections one
    from collections import OrderedDict  # noqa


def get_profiler_dir():
    return os.environ.get("PYMALCOLM_PROFILER_DIR", "/tmp/imalcolm_profiles")


def get_stack_size():
    return int(os.environ.get("PYMALCOLM_STACK_SIZE", "0"))


def et_to_string(element: ET.Element) -> str:
    xml = '<?xml version="1.0" ?>'
    try:
        xml += ET.tostring(element, encoding="unicode")
    except LookupError:
        xml += ET.tostring(element).decode()
    return xml


# Exception handling from future.utils
def raise_with_traceback(exc, traceback=Ellipsis):
    if traceback == Ellipsis:
        _, _, traceback = sys.exc_info()
    raise exc.with_traceback(traceback)
