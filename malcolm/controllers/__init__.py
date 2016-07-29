# make the import path nice
from malcolm.util import import_child_packages

class_dict = import_child_packages("controllers")

globals().update(class_dict)
__all__ = list(class_dict)

del class_dict
del import_child_packages
