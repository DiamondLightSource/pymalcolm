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
        func_tasks = {}

        # Filter part tasks so that we only run the ones hooked to us
        for part, task in part_tasks.items():
            for func_name, part_hook, func in get_hook_decorated(part):
                if part_hook is self:
                    assert func not in func_tasks, \
                        "Function %s is second defined for a hook" % func_name
                    func_tasks[func] = task

        return func_tasks

    def make_return_table(self, part_tasks):
        # Filter part tasks so that we only run the ones hooked to us
        columns = OrderedDict(name=StringArrayMeta("Part name"))
        for part in part_tasks:
            hooked = [method_name for (method_name, hook, _) in
                      get_hook_decorated(part) if hook is self]
            for method_name, method_meta, func in get_method_decorated(part):
                if method_name in hooked:
                    # Add return metas to the table columns
                    for arg_name in method_meta.returns.elements:
                        md = method_meta.returns.elements[arg_name].to_dict()
                        if "ArrayMeta" in md["typeid"]:
                            md["tags"] = md["tags"] + ["hook:return_array"]
                        else:
                            md["typeid"] = md["typeid"].replace(
                                "Meta", "ArrayMeta")
                        meta = deserialize_object(md, VArrayMeta)
                        if arg_name in columns:
                            column_d = columns[arg_name].to_dict()
                            assert column_d == md, \
                                "%s != %s" % (column_d, md)
                        columns[arg_name] = meta
        meta = TableMeta("Part returns from hook", columns=columns)
        return_table = Table(meta)
        return return_table


def get_hook_decorated(part):
    for name, member in inspect.getmembers(part, inspect.ismethod):
        if hasattr(member, "Hook"):
            yield name, member.Hook, member
