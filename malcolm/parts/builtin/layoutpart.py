from malcolm.core import Part, REQUIRED, method_takes
from malcolm.core.vmetas import StringMeta


@method_takes("child", StringMeta("Name of child object"), REQUIRED)
class LayoutPart(Part):
    # Child block object
    child = None

    def store_params(self, params):
        self.child = self.process.get_block(params.child)
