from malcolm.core import Info

dataset_types = [
    "primary", "secondary", "monitor", "position_set", "position_value"]


class DatasetProducedInfo(Info):
    def __init__(self, name, filename, type, rank, path, uniqueid):
        self.name = name
        self.filename = filename
        assert type in dataset_types, \
            "Dataset type %s not in %s" % (type, dataset_types)
        self.type = type
        self.rank = rank
        self.path = path
        self.uniqueid = uniqueid


