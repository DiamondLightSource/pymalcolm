from malcolm.core import Part
from malcolm.core.vmetas import ChoiceMeta


class PandABoxGroupPart(Part):
    """This will normally be instantiated by the PandABox assembly, not created
    in yaml"""

    def __init__(self, process, attr_name):
        params = Part.MethodMeta.prepare_input_map(name=attr_name)
        super(PandABoxGroupPart, self).__init__(process, params)
        self.attr_name = attr_name
        self.attr = None

    def create_attributes(self):
        tags = ["widget:group"]
        meta = ChoiceMeta("All %s attributes" % self.attr_name,
                          choices=["expanded", "collapsed"], tags=tags,
                          label=self.attr_name.title())
        self.attr = meta.make_attribute("expanded")
        yield self.attr_name, self.attr, self.attr.set_value

