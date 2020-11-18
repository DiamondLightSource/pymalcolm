# Expose a nice namespace
from malcolm.core import submodule_all

from .profilingviewerpart import ProfilingViewerPart

__all__ = submodule_all(globals())
