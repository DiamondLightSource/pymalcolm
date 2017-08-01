from malcolm.core import method_takes, REQUIRED, create_class_params
from malcolm.modules.builtin.vmetas import ChoiceMeta, StringMeta
from .attributepart import AttributePart


@method_takes(
    "name", StringMeta("Name of the created attribute"), REQUIRED,
    "description", StringMeta("Desc of created attribute"), REQUIRED)
class GroupPart(AttributePart):
    """Part representing a GUI group other attributes attach to"""
    def __init__(self, params):
        params = create_class_params(
            super(GroupPart, self),
            widget="group", writeable=True, config=True, **params)
        super(GroupPart, self).__init__(params)

    def get_initial_value(self):
        return "expanded"

    def create_meta(self, description, tags):
        return ChoiceMeta(
            choices=["expanded", "collapsed"],
            description=description, tags=tags)
