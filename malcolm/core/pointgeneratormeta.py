from malcolm.core.attributemeta import AttributeMeta
from scanpointgenerator import CompoundGenerator


@AttributeMeta.register("malcolm:core/PointGenerator:1.0")
class PointGeneratorMeta(AttributeMeta):

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

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = super(PointGeneratorMeta, self).to_dict()

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a PointGeneratorMeta subclass instance from the
        version of itself

        Args:
            name (str): AttributeMeta instance name
            d (dict): Serialised version of PointGeneratorMeta
        """

        point_gen_meta = PointGeneratorMeta(name, d["description"])
        return point_gen_meta

    def attribute_type(self):
        return AttributeMeta.SCALAR
