import inspect

from malcolm.compat import OrderedDict


class Info(object):
    """Base class that should be inherited from when a part needs to return
    something from a hooked function"""

    def __repr__(self):
        spec = inspect.getargspec(self.__init__)
        args = ", ".join(repr(getattr(self, x)) for x in spec.args[1:])
        return "%s(%s)" % (self.__class__.__name__, args)

    @classmethod
    def filter_parts(cls, part_info):
        """Filter the part_info dict looking for instances of our class

        Args:
            part_info (dict): {part_name: [Info] or None} as returned from
                Controller.run_hook()

        Returns:
            dict: {part_name: [info]} where info is a subclass of cls
        """
        filtered = OrderedDict()
        for part_name, info_list in part_info.items():
            if info_list is None:
                continue
            info_list = [i for i in info_list if isinstance(i, cls)]
            if info_list:
                filtered[part_name] = info_list
        return filtered

    @classmethod
    def filter_values(cls, part_info):
        """Filter the part_info dict list looking for instances of our class

        Args:
            part_info (dict): {part_name: [Info] or None} as returned from
                Controller.run_hook()

        Returns:
            list: [info] where info is a subclass of cls
        """
        filtered = []
        for info_list in cls.filter_parts(part_info).values():
            filtered += info_list
        return filtered
