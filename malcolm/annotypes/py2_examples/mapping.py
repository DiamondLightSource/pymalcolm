from annotypes import Anno, WithCallTypes, Mapping, Any

from .table import LayoutTable

with Anno("Layouts for objects"):
    PartLayout = Mapping[str, LayoutTable]
with Anno("The default value we should use"):
    Value = Any


class LayoutManager(WithCallTypes):
    def __init__(self, part_layout, value):
        # type: (PartLayout, Value) -> None
        self.part_layout = part_layout
        self.value = value
