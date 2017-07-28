import os
import sys
import importlib
import logging
import types
import imp

# Create a module level logger
log = logging.getLogger(__name__)


class Importer(object):
    def __init__(self, ):
        self.special_names = [
            "vmetas", "infos", "controllers", "parts", "includes", "blocks"]

    def import_all_packages(self, root_package, root_init, globals_d):
        """Import any packages relative to self.root_dir, recursing down one
        level to specially named subdirs"""
        modules = {}
        root_dir = os.path.dirname(root_init)
        for f in os.listdir(root_dir):
            if os.path.isfile(os.path.join(root_dir, f, "__init__.py")):
                name = ".".join([root_package, f])
                modules.update(self.try_import_name(name))
                pkg_dir = os.path.join(root_dir, f)
                self.import_special_subpackages(name, pkg_dir)
        globals_d.update(modules)
        return list(modules)

    def import_special_subpackages(self, name, path):
        """Import specially named subpackages of name"""
        for n in self.special_names:
            sub_dir = os.path.join(path, n)
            if os.path.isdir(sub_dir) or os.path.isfile(sub_dir + ".py"):
                self.try_import_name(".".join([name, n]))

    def try_import_name(self, name):
        try:
            imp = importlib.import_module(name)
        except ImportError:
            log.warning("Importing %s failed", name, exc_info=True)
            return {}
        else:
            return {name: imp}

    def import_package_from_path(self, name, path):
        dirname, basename = os.path.abspath(path).rsplit(os.sep, 1)
        file, pathname, description = imp.find_module(basename, [dirname])
        try:
            mod = imp.load_module(name, file, pathname, description)
        finally:
            if file is not None:
                file.close()
        parent_name, attr_name = name.rsplit(".", 1)
        parent = importlib.import_module(parent_name)
        setattr(parent, attr_name, mod)
