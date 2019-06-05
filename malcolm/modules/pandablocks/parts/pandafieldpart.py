from annotypes import Anno, Any

from malcolm.core import Part, snake_to_camel, BooleanMeta, VMeta, \
    PartRegistrar, TimeStamp, Alarm
from ..pandablocksclient import PandABlocksClient


with Anno("Client for setting and getting field"):
    AClient = PandABlocksClient
with Anno("Meta object to create attribute from"):
    AMeta = VMeta
with Anno("Name of Block in TCP server"):
    ABlockName = str
with Anno("Name of Field in TCP server"):
    AFieldName = str
with Anno("Initial value of attribute"):
    AInitialValue = Any


class PandAFieldPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, client, meta, block_name, field_name,
                 initial_value=None):
        # type: (AClient, AMeta, ABlockName, AFieldName, AInitialValue) -> None
        part_name = field_name.replace(".", "_")
        super(PandAFieldPart, self).__init__(part_name)
        self.client = client
        self.meta = meta
        self.block_name = block_name
        self.field_name = field_name
        self.attr = self.meta.create_attribute_model(initial_value)
        self.pending_change = False

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(PandAFieldPart, self).setup(registrar)
        attr_name = snake_to_camel(self.field_name.replace(".", "_"))
        if self.meta.writeable:
            writeable_func = self.set_field
        else:
            writeable_func = None
        registrar.add_attribute_model(attr_name, self.attr, writeable_func)

    def handle_change(self, value, ts):
        # type: (str, TimeStamp) -> None
        value = self.attr.meta.validate(value)
        if self.pending_change:
            self.pending_change = False
            if value == self.attr.value:
                # Ignore this change
                return
        self.attr.set_value_alarm_ts(value, Alarm.ok, ts)

    def set_field(self, value):
        if isinstance(self.meta, BooleanMeta):
            value = int(value)
        # Mark the next change as a possible duplicate
        self.pending_change = True
        self.client.set_field(self.block_name, self.field_name, value)
        self.attr.set_value(value)

