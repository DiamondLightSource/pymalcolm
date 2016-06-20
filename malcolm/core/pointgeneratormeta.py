from malcolm.core.attributemeta import AttributeMeta
from scanpointgenerator import Generator


@AttributeMeta.register_subclass("malcolm:core/PointGenerator:1.0")
class PointGeneratorMeta(AttributeMeta):

    def __init__(self, name, description):
        super(PointGeneratorMeta, self).__init__(name, description)

        self.name = name

    def validate(self, value):
        if not isinstance(value, Generator):
            raise TypeError("Value must be of type Generator")

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
