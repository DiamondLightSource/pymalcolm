from malcolm.parts.ca.castringpart import CAStringPart
from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta

@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED,
    "rbv", StringMeta("Full pv of demand and default for rbv"), REQUIRED,
    "outportType", StringMeta("Type (like 'CS' or 'NDArray')"), REQUIRED,
)
class AsynOutportPart(CAStringPart):

    def __init__(self, process, params):
        params = params.to_dict()
        self.outport_type = params.pop("outportType")
        params = CAStringPart.MethodMeta.prepare_input_map(params)
        super(AsynOutportPart, self).__init__(process, params)

    def create_tags(self, params):
        tags = ["widget:textupdate"]
        return tags

    @DefaultController.Resetting
    def connect_pvs(self, _=None):
        super(AsynOutportPart, self).connect_pvs()
        # Add the outport tags
        tags = [t for t in self.attr.meta.tags
                if not t.startswith("flowgraph:outport:")]
        tags.append("flowgraph:outport:%s:%s" % (
            self.outport_type, self.attr.value))
