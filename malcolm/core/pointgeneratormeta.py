from malcolm.core.scalarmeta import ScalarMeta
from scanpointgenerator import CompoundGenerator


@ScalarMeta.register("malcolm:core/PointGenerator:1.0")
class PointGeneratorMeta(ScalarMeta):

    def __init__(self, name, description):
        super(PointGeneratorMeta, self).__init__(name, description)

        self.name = name

    def validate(self, value):

        if isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, dict):
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError("Value must be a Generator object or dictionary")
