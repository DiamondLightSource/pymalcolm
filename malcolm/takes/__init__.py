from malcolm.core.package import register_package

class_dict = register_package("takes")

globals().update(class_dict)
__all__ = list(class_dict)

del class_dict
