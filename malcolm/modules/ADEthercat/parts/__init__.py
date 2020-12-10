# Expose a nice namespace
from malcolm.core import submodule_all

from .ethercatdriverpart import EthercatDriverPart

__all__ = submodule_all(globals())
