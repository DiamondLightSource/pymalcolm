from malcolm.compat import OrderedDict


class Info(object):
    """Base class that should be inherited from when a part needs to return
    something from a hooked function"""

    @classmethod
    def filter(cls, part_info):
        """Filter the part_info dict looking for instances of ourself

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
