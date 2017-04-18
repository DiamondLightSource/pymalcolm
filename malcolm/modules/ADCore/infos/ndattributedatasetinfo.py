from malcolm.core import Info


attribute_dataset_types = ["detector", "monitor", "position"]


class NDAttributeDatasetInfo(Info):
    def __init__(self, name, type, attr, rank):
        self.name = name
        assert type in attribute_dataset_types, \
            "Dataset type %s not in %s" % (type, attribute_dataset_types)
        self.type = type
        self.attr = attr
        self.rank = rank


