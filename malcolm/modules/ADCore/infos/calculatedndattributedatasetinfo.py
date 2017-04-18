from malcolm.core import Info


class CalculatedNDAttributeDatasetInfo(Info):
    def __init__(self, name, attr):
        self.name = name
        self.attr = attr
