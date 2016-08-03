import os
import importlib
import logging


def import_child_packages(package_name):
    """Prepare a package namespace by importing all subclasses following PEP8
    rules that have @takes decorated functions"""
    class_dict = {}
    # this is the path to the package
    package_path = os.path.join(os.path.dirname(__file__), package_name)
    for f in os.listdir(package_path):
        if f.endswith(".py") and f != "__init__.py":
            # import it and see what it produces
            module_name = f[:-3]
            module = importlib.import_module(
                "malcolm.%s.%s" % (package_name, module_name))
            for cls in find_decorated_classes(module):
                class_dict[cls.__name__] = cls
    return class_dict


def find_decorated_classes(module):
    for n in dir(module):
        cls = getattr(module, n)
        if hasattr(cls, "MethodMeta"):
            module_name = module.__name__.split(".")[-1]
            if n.lower() != module_name:
                logging.warning("Classname %s when lower cased should be %s" %
                                (n, module_name))
            logging.debug("Found child class %s" % cls)
            yield cls
