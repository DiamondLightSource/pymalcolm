# Expose a nice namespace
from malcolm.core import submodule_all

from .ProcessController import ProcessController

__all__ = submodule_all(globals())
