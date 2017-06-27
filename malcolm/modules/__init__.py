class Importer(object):
    def __init__(self):
        self.update_dict = {}
        self.ignore = ["docs"]

    def import_subpackages(self, path):
        import os
        dirname = os.path.join(os.path.dirname(__file__), *path)
        for f in os.listdir(dirname):
            if f not in self.ignore and os.path.isdir(os.path.join(dirname, f)):
                self.try_import_path(path + [f])

    def try_import_path(self, path):
        import importlib
        name = ".".join(path)
        try:
            self.update_dict[name] = importlib.import_module(
                "malcolm.modules.%s" % name)
        except ImportError:
            import logging
            # Create a module level logger
            log = logging.getLogger(__name__)
            log.info("Importing %s failed", name, exc_info=True)
        # Try the import of subpackages too
        self.import_subpackages(path)

    def prepare(self, globals_d):
        self.import_subpackages([])
        globals_d.update(self.update_dict)
        __all__ = list(self.update_dict)
        return __all__

__all__ = Importer().prepare(globals())

del Importer
