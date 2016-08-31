import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from pkg_resources import require
require("mock", "numpy", "tornado", "cothread", "ruamel.yaml",
        "scanpointgenerator")

from mock import MagicMock

try:
    import cothread
except:
    # cothread doesn't work on python3 at the moment
    cothread = MagicMock()
    # Tell Mock not to have a MethodMeta, otherwise we will be decorated
    del cothread.MethodMeta
    def callback_result(f, *args, **kwargs):
        return f(*args, **kwargs)
    cothread.CallbackResult.side_effect = callback_result
    sys.modules["cothread"] = cothread
catools = MagicMock()
# Tell Mock not to have a MethodMeta, otherwise we will be decorated
del catools.MethodMeta
cothread.catools = catools

# Mock out pvaccess
sys.modules['pvaccess'] = MagicMock()
# Tell Mock not to have a MethodMeta, otherwise we will be decorated
import pvaccess
del pvaccess.MethodMeta