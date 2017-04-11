from malcolm.controllers.builtin import StatefulController
from malcolm.core import method_takes, REQUIRED, call_with_params
from malcolm.parts.ca.castringpart import CAStringPart
from malcolm.tags import port_types, outport, widget
from malcolm.vmetas.builtin import StringMeta, ChoiceMeta


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "rbv", StringMeta("Full pv of demand and default for rbv"), REQUIRED,
    "outport", ChoiceMeta("Outport type", port_types), REQUIRED)
class AsynOutportPart(CAStringPart):
    def __init__(self, params):
        args = CAStringPart.MethodModel.prepare_call_args(
            name=params.name, description=params.description, rbv=params.rbv)
        super(AsynOutportPart, self).__init__(*args)

    def create_tags(self):
        tags = super(AsynOutportPart, self).create_tags()
        tags.append(widget("textupdate"))
        return tags

    @StatefulController.Reset
    def reset(self, task=None):
        super(AsynOutportPart, self).reset(task)
        # Add the outport tags
        tags = [t for t in self.attr.meta.tags if not t.startswith("outport:")]
        tags.append(outport(self.outport_type, self.attr.value))
        self.attr.meta.set_tags(tags)
