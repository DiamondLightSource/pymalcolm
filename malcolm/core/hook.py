import inspect
from collections import OrderedDict

from malcolm.core.methodmeta import MethodMeta, get_method_decorated
from malcolm.core.vmetas import StringArrayMeta, TableMeta
from malcolm.core.serializable import deserialize_object
from malcolm.core.varraymeta import VArrayMeta
from malcolm.core.table import Table


class Hook(object):

    def __call__(self, func):
        """
        Decorator function to add a Hook to a Part's function

        Args:
            func: Function to decorate with Hook

        Returns:
            Decorated function
        """

        func.Hook = self
        MethodMeta.wrap_method(func)
        return func

    def find_hooked_functions(self, parts):
        # Filter part dict to find parts that have a function hooked to us
        part_funcs = {}

        for part_name, part in parts.items():
            for func_name, part_hook, func in get_hook_decorated(part):
                if part_hook is self:
                    assert part_name not in part_funcs, \
                        "Function %s is second defined for a hook" % func_name
                    part_funcs[part_name] = func_name

        return part_funcs


def get_hook_decorated(part):
    for name, member in inspect.getmembers(part, inspect.ismethod):
        if hasattr(member, "Hook"):
            yield name, member.Hook, member
