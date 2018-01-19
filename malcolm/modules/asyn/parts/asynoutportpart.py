from annotypes import Anno, Any

from malcolm.core import Part, PartRegistrar, StringMeta, Hook, Port
from malcolm.modules import ca


with Anno("Outport type"):
    AOutport = Port


class AsynOutportPart(Part):
    """Defines a string `Attribute` representing a asyn port that should be
    depicted as an outport on a Block"""

    def __init__(self,
                 name,  # type: ca.util.APartName
                 description,  # type: ca.util.AMetaDescription
                 rbv,  # type: ca.util.ARbv
                 outport,  # type: AOutport
                 group=None  # type: ca.util.AGroup
                 ):
        # type: (...) -> None
        super(AsynOutportPart, self).__init__(name)
        self.outport = outport
        self.meta = StringMeta(description)
        catools = ca.util.CaToolsHelper.instance()
        self.caa = ca.util.CAAttribute(
            self.meta, catools.DBR_STRING, rbv=rbv, group=group,
            on_connect=self.update_tags)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.caa.setup(registrar, self.name)

    def on_hook(self, hook):
        # type: (Hook) -> None
        self.caa.on_hook(hook)

    def update_tags(self, value):
        # type: (Any) -> None
        # Add the outport tags
        old_tags = self.meta.tags
        new_tags = [t for t in old_tags if not t.startswith("outport:")]
        new_tags.append(self.outport.outport_tag(connected_value=value))
        if old_tags != new_tags:
            self.meta.set_tags(new_tags)
