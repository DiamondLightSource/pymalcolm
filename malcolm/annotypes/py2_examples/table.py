from annotypes import Anno, WithCallTypes, Array, add_call_types


class Table(WithCallTypes):
    def validate(self):
        lengths = {a: len(getattr(self, a)) for a in self.call_types}
        assert len(set(lengths.values())) == 1, \
            "Column lengths %s don't match" % lengths

    def __getitem__(self, item):
        self.validate()
        return [getattr(self, a)[item] for a in self.call_types]


with Anno("Name of layout part"):
    Name = Array[str]
with Anno("Malcolm full name of child block"):
    MRI = Array[str]
with Anno("X Coordinate of child block"):
    X = Array[float]
with Anno("Y Coordinate of child block"):
    Y = Array[float]
with Anno("Whether child block is visible"):
    Visible = Array[bool]


class LayoutTable(Table):
    def __init__(self, name, mri, x, y, visible):
        # type: (Name, MRI, X, Y, Visible) -> None
        self.name = name
        self.mri = mri
        self.x = x
        self.y = y
        self.visible = visible


with Anno("The layout table to act on"):
    ALayout = LayoutTable


class Manager(WithCallTypes):
    layout = None  # type: ALayout

    @add_call_types
    def set_layout(self, value):
        # type: (ALayout) -> None
        self.layout = value
