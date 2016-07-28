import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scanpointgenerator"))

from pkg_resources import require
require("mock", "numpy", "tornado", "cothread")

from mock import MagicMock

try:
    import cothread
except:
    # cothread doesn't work on python3 at the moment
    cothread = MagicMock()
    def callback_result(f, *args, **kwargs):
        return f(*args, **kwargs)
    cothread.CallbackResult.side_effect = callback_result
    sys.modules["cothread"] = cothread
catools = MagicMock()
cothread.catools = catools
