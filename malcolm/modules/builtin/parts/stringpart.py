from annotypes import Anno

from malcolm.core import Part, Registrar
from malcolm.core.vmetas import StringMeta
from ..util import set_tags, Name, Description, Writeable, Config, Group, AWidget


with Anno("Initial value of the created attribute"):
    Value = str


class StringPart(Part):
    """Create a single string Attribute on the Block"""
    def __init__(self,
                 name,  # type: Name
                 description,  # type: Description
                 writeable=False,  # type: Writeable
                 config=True,  # type: Config
                 group=None,  # type: Group
                 widget=None,  # type: AWidget
                 value="",  # type: Value
                 ):
        # type: (...) -> None
        super(StringPart, self).__init__(name)
        meta = StringMeta(description)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar):
        # type: (Registrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
