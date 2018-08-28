from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta
from ..infos import TitleInfo
from ..util import set_tags


with Anno("Initial value of Block label"):
    Value = str


class TitlePart(Part):
    """Part representing a the title of the Block a GUI should display"""
    def __init__(self, value):
        # type: (Value) -> None
        super(TitlePart, self).__init__("label")
        meta = StringMeta("Label for the block")
        set_tags(meta, writeable=True)
        self.attr = meta.create_attribute_model()
        self.registrar = None  # type: PartRegistrar
        self.initial_value = value

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.registrar = registrar
        registrar.add_attribute_model(self.name, self.attr, self.set_label)
        self.set_label(self.initial_value)

    def set_label(self, value):
        self.attr.set_value(value)
        self.registrar.report(TitleInfo(value))
