import os
import importlib
import logging


def import_methodmeta_decorated_classes(globals_d, package_name):
    return import_pep8_named_classes(globals_d, package_name, True)


def import_pep8_named_classes(globals_d, package_name, only_methodmeta=False):
    """Prepare a package namespace by importing all subclasses following PEP8
    rules that have @takes decorated functions"""
    def finder(package_fs_path, fname):
        if fname.endswith(".py") and fname != "__init__.py":
            # import it and see what it produces
            import_name = "%s.%s" % (package_name, fname[:-3])
            logging.debug("Importing %s" % import_name)
            module = importlib.import_module(import_name)
            for n in dir(module):
                cls = getattr(module, n)
                module_name = module.__name__.split(".")[-1]
                if n.lower() == module_name:
                    if only_methodmeta:
                        found = hasattr(cls, "MethodMeta")
                    else:
                        found = True
                    logging.debug("Found child class %s" % cls)
                    yield cls.__name__, cls

    __all__ = prepare_globals_for_package(globals_d, package_name, finder)
    return __all__


def import_sub_packages(globals_d, package_name):
    def finder(package_fs_path, fname):
        if os.path.isdir(os.path.join(package_fs_path, fname)):
            # import it and add it to the list
            import_name = "%s.%s" % (package_name, fname)
            logging.debug("Importing %s", import_name)
            module = importlib.import_module(import_name)
            yield fname, module

    __all__ = prepare_globals_for_package(globals_d, package_name, finder)
    return __all__


def prepare_globals_for_package(globals_d, package_name, finder):

    update_dict = {}

    # this is the path to the package
    package_relative = package_name.split(".")[1:]
    package_fs_path = os.path.join(os.path.dirname(__file__), *package_relative)

    for f in os.listdir(package_fs_path):
        for name, ob in finder(package_fs_path, f):
            update_dict[name] = ob

    globals_d.update(update_dict)
    __all__ = list(update_dict)
    return __all__







