import os
import importlib
import logging


def import_methodmeta_decorated_classes(globals_d, package_name):
    """Prepare a package namespace by importing all subclasses following PEP8
    rules that have @takes decorated functions"""
    class_dict = {}
    # this is the path to the package
    package_relative = package_name.split(".")[1:]
    package_fs_path = os.path.join(os.path.dirname(__file__), *package_relative)

    for f in os.listdir(package_fs_path):
        if f.endswith(".py") and f != "__init__.py":
            # import it and see what it produces
            import_name = "%s.%s" % (package_name, f[:-3])
            logging.debug("Importing %s" % import_name)
            module = importlib.import_module(import_name)
            for cls in find_decorated_classes(module):
                class_dict[cls.__name__] = cls

    globals_d.update(class_dict)
    __all__ = list(class_dict)
    return __all__


def import_sub_packages(globals_d, package_name):
    module_dict = {}
    # this is the path to the package
    package_relative = package_name.split(".")[1:]
    package_fs_path = os.path.join(os.path.dirname(__file__), *package_relative)

    logging.debug("Importing sub packages from %s" % package_fs_path)
    for f in os.listdir(package_fs_path):
        if os.path.isdir(os.path.join(package_fs_path, f)):
            # import it and add it to the list
            import_name = "%s.%s" % (package_name, f)
            logging.debug("Importing %s", import_name)
            module = importlib.import_module(import_name)
            module_dict[f] = module

    globals_d.update(module_dict)
    __all__ = list(module_dict)
    return __all__


def find_decorated_classes(module):
    for n in dir(module):
        cls = getattr(module, n)
        if hasattr(cls, "MethodMeta"):
            module_name = module.__name__.split(".")[-1]
            if n.lower() == module_name:
                logging.debug("Found child class %s" % cls)
                yield cls
