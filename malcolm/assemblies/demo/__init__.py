# make assemblies from all YAML files
from malcolm.assemblyutil import make_all_assemblies

__all__ = make_all_assemblies(globals(), __name__)

del make_all_assemblies
