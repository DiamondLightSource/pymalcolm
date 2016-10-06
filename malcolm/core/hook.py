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

    def find_func_tasks(self, part_tasks):
        # {func: Task}
        func_tasks = {}

        # Filter part tasks so that we only run the ones hooked to us
        for part, task in part_tasks.items():
            for func_name, part_hook, func in get_hook_decorated(part):
                if part_hook is self:
                    assert func not in func_tasks, \
                        "Function %s is second defined for a hook" % func_name
                    func_tasks[func] = task

        return func_tasks

    def find_hooked_functions(self, parts):
        # Filter part tasks so that we only run the ones hooked to us
        # {part_name: func}
        part_funcs = {}

        for part_name, part in parts.items():
            for func_name, part_hook, func in get_hook_decorated(part):
                if part_hook is self:
                    part_funcs[part_name] = func

        return part_funcs

def get_hook_decorated(part):
    for name, member in inspect.getmembers(part, inspect.ismethod):
        if hasattr(member, "Hook"):
            yield name, member.Hook, member
