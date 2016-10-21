from collections import OrderedDict


class Info(object):
    @classmethod
    def filter(cls, part_info):
        filtered = OrderedDict()
        for part_name, info_list in part_info.items():
            if info_list is None:
                continue
            info_list = [i for i in info_list if isinstance(i, cls)]
            if info_list:
                filtered[part_name] = info_list
        return filtered
