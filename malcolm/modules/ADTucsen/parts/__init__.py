# Expose a nice namespace
from malcolm.core import submodule_all

from .tucsendriverpart import AMri, APartName, TucsenDriverPart

__all__ = submodule_all(globals())
