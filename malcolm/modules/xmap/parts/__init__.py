# Find all subpackages, MethodMeta decorated callables, and YAML files
from malcolm.packageutil import prepare_package

__all__ = prepare_package(globals(), __name__)

del prepare_package
