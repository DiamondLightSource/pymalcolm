from malcolm.core import Part, method_takes, REQUIRED
from malcolm.core.vmetas import StringMeta


@method_takes(
    "name", StringMeta("Name of the Part within the controller"), REQUIRED)
class DummyPart(Part):
    """Defines a dummy part"""
    def __init__(self, params):
        super(DummyPart, self).__init__(params.name)
