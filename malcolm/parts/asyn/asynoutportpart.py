from malcolm.parts.ca.castringpart import CAStringPart
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta, ChoiceMeta
from malcolm.tags import port_types, outport, widget

@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "rbv", StringMeta("Full pv of demand and default for rbv"), REQUIRED,
    "outport", ChoiceMeta("Outport type", port_types), REQUIRED)
class AsynOutportPart(CAStringPart):

    def __init__(self, process, params):
        self.outport_type = params.outportType
        params = CAStringPart.MethodMeta.prepare_input_map(
            name=params.name, description=params.description, rbv=params.rbv)
        super(AsynOutportPart, self).__init__(process, params)

    def create_tags(self, params):
        tags = [widget("textupdate")]
        return tags

    @DefaultController.Reset
    def reset(self, task=None):
        super(AsynOutportPart, self).reset(task)
        # Add the outport tags
        tags = [t for t in self.attr.meta.tags if not t.startswith("outport:")]
        tags.append(outport(self.outport_type, self.attr.value))
