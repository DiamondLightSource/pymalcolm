import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "scanpointgenerator"))

from pkg_resources import require
require("mock", "numpy", "tornado", "cothread")
