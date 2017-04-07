from malcolm.core import Info


class NDArrayDatasetInfo(Info):
    def __init__(self, name, rank):
        self.name = name
        self.rank = rank
