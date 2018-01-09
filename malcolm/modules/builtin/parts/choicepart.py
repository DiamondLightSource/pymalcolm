from annotypes import Anno, Array

from malcolm.core import Part, Registrar
from malcolm.core.vmetas import ChoiceMeta
from ..util import set_tags, Name, Description, Writeable, Config, Group, AWidget


with Anno("Possible choices for this attribute"):
    Choices = Array[str]
with Anno("Initial value of the created attribute"):
    Value = str


class ChoicePart(Part):
    """Create a single choice Attribute on the Block"""
    def __init__(self,
                 name,  # type: Name
                 description,  # type: Description
                 choices,  # type: Choices
                 value,  # type: Value
                 writeable=False,  # type: Writeable
                 config=True,  # type: Config
                 group=None,  # type: Group
                 widget=None,  # type: AWidget
                 ):
        # type: (...) -> None
        super(ChoicePart, self).__init__(name)
        meta = ChoiceMeta(description, choices)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar):
        # type: (Registrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)

