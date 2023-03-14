# Expose a nice namespace
from malcolm.core import submodule_all

from .xspresswriterpart import AMri, APartName, XspressWriterPart

__all__ = submodule_all(globals())
