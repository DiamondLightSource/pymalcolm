from malcolm.core import Part
from malcolm.core.vmetas import ChoiceMeta
from malcolm.tags import widget, config


class PandABoxGroupPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, attr_name):
        params = Part.MethodMeta.prepare_input_map(name=attr_name)
        super(PandABoxGroupPart, self).__init__(process, params)
        self.attr_name = attr_name
        tags = [widget("group"), config()]
        self.meta = ChoiceMeta(
            "All %s attributes" % self.attr_name,
            choices=["expanded", "collapsed"], tags=tags,
            label=self.attr_name.title())

    def create_attributes(self):
        attr = self.meta.make_attribute("expanded")
        yield self.attr_name, attr, attr.set_value

