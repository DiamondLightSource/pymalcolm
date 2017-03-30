from scanpointgenerator import CompoundGenerator

from malcolm.core.ntunion import NTUnion
from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
class PointGeneratorMeta(VMeta):

    attribute_class = NTUnion

    def validate(self, value):
        if value is None:
            return CompoundGenerator([], [], [])
        elif isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, dict):
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)
