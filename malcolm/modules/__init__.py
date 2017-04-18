class Importer(object):
    def __init__(self):
        self.update_dict = {}

    def import_subpackages(self, path):
        import os
        import importlib
        dirname = os.path.join(os.path.dirname(__file__), *path)
        for f in os.listdir(dirname):
            if os.path.isdir(os.path.join(dirname, f)):
                name = ".".join(path + [f])
                self.update_dict[name] = importlib.import_module(
                    "malcolm.modules.%s" % name)
                # Try the import of subpackages too
                self.import_subpackages(path + [f])

    def prepare(self, globals_d):
        self.import_subpackages([])
        globals_d.update(self.update_dict)
        __all__ = list(self.update_dict)
        return __all__

__all__ = Importer().prepare(globals())

del Importer
