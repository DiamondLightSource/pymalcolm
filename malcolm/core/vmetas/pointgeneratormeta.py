from collections import OrderedDict

from scanpointgenerator import CompoundGenerator

from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
class PointGeneratorMeta(VMeta):

    def validate(self, value):
        if value is None or isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, (OrderedDict, dict)):
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)