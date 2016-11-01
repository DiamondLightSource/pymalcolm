import os
import importlib
import logging


try:
    from malcolm.yamlutil import make_block_creator, make_include_creator
except ImportError:
    make_creator = None
else:
    def make_creator(package_name):
        if package_name.startswith("malcolm.blocks."):
            return make_block_creator
        elif package_name.startswith("malcolm.includes."):
            return make_include_creator


def find_package_contents(package_name, package_fs_path, fname):
    if fname.endswith(".py") and fname != "__init__.py":
        # import it and see what it produces
        import_name = "%s.%s" % (package_name, fname[:-3])
        logging.debug("Importing %s", import_name)
        module = importlib.import_module(import_name)
        for n in dir(module):
            cls = getattr(module, n)
            module_name = module.__name__.split(".")[-1]
            if n.lower() == module_name:
                if hasattr(cls, "MethodMeta"):
                    logging.debug("Found child class %s", cls)
                    yield cls.__name__, cls
    elif os.path.isdir(os.path.join(package_fs_path, fname)):
        # import it and add it to the list
        import_name = "%s.%s" % (package_name, fname)
        logging.debug("Importing %s", import_name)
        try:
            module = importlib.import_module(import_name)
        except Exception:
            logging.exception("Importing %s failed", import_name)
        else:
            yield fname, module
    elif fname.endswith(".yaml"):
        # check we need to do something with it
        creator = make_creator(package_name)
        if creator:
            # load the yaml file and make an assembly out of it
            split = fname.split(".")
            assert len(split) == 2, \
                "Expected <something_without_dots>.yaml, got %r" % fname
            yaml_path = os.path.join(package_fs_path, fname)
            logging.debug("Parsing %s", yaml_path)
            with open(yaml_path) as f:
                text = f.read()
                try:
                    func = creator(text)
                except Exception:
                    logging.exception("Creating object from %s failed", fname)
                else:
                    yield split[0], func


def prepare_package(globals_d, package_name):
    """Prepare a package namespace by importing all subclasses following PEP8
    rules that have @takes decorated functions, and all subpackages"""
    __all__ = prepare_globals_for_package(
        globals_d, package_name, find_package_contents)
    return __all__


def prepare_globals_for_package(globals_d, package_name, finder):

    update_dict = {}

    # this is the path to the package
    package_relative = package_name.split(".")[1:]
    package_fs_path = os.path.join(os.path.dirname(__file__), *package_relative)

    for f in os.listdir(package_fs_path):
        for name, ob in finder(package_name, package_fs_path, f):
            update_dict[name] = ob

    globals_d.update(update_dict)
    __all__ = list(update_dict)
    return __all__
