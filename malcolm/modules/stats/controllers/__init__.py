from .statscontroller import StatsController, parse_yaml_version

# Expose a nice namespace
from malcolm.core import submodule_all

__all__ = submodule_all(globals())
