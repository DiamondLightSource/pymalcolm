import os
import importlib

from malcolm.core.serializable import Serializable


def register_package(package_name):
    """Prepare a package namespace by importing all subclasses following PEP8
    rules, and registering any @takes decorated functions"""
    class_dict = {}
    malcolm_path = os.path.join(os.path.dirname(__file__), "..")
    # this is the path to the package
    package_path = os.path.join(malcolm_path, package_name)
    for f in os.listdir(package_path):
        if f.endswith(".py") and f != "__init__.py":
            # import it and see what it produces
            module_name = f[:-3]
            module = importlib.import_module(
                "malcolm.%s.%s" % (package_name, module_name))
            for n in dir(module):
                if n.lower() == module_name:
                    cls = getattr(module, n)
                    if hasattr(cls, "Method"):
                        # we have something!
                        class_dict[cls.__name__] = cls
                        register_name = "%s.%s" % (package_name, cls.__name__)
                        Serializable.register_subclass(register_name)(cls)
    return class_dict
