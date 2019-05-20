from annotypes import Anno

from malcolm.core import Part, PartRegistrar, StringMeta
from ..infos import LabelInfo
from ..util import set_tags


with Anno("Initial value of Block label"):
    ALabelValue = str


class LabelPart(Part):
    """Part representing a the title of the Block a GUI should display"""
    def __init__(self, value=None):
        # type: (ALabelValue) -> None
        super(LabelPart, self).__init__("label")
        meta = StringMeta("Label for the block")
        set_tags(meta, writeable=True)
        self.initial_value = value
        self.attr = meta.create_attribute_model(self.initial_value)

    def _report(self):
        self.registrar.report(LabelInfo(self.attr.value))

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(LabelPart, self).setup(registrar)
        registrar.add_attribute_model(self.name, self.attr, self.set_label)
        self._report()

    def set_label(self, value, ts=None):
        self.attr.set_value(value, ts=ts)
        self._report()
