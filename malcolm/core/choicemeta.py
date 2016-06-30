from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(ScalarMeta):
    """Meta object containing information for a enum"""

    def __init__(self, name, description, oneOf):
        super(ChoiceMeta, self).__init__(name=name, description=description)

        self.oneOf = oneOf

    def set_one_of(self, oneOf):
        """
        Set allowed values

        Args:
            oneOf(list): List of allowed values
        """

        self.oneOf = oneOf

    def validate(self, value):
        """
        Check if the value is valid returns it

        Args:
            value: Value to validate

        Returns:
            Value if it is valid
        Raises:
            ValueError: If value not valid
        """

        if value in self.oneOf:
            return value
        else:
            raise ValueError("%s is not a valid value" % value)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = super(ChoiceMeta, self).to_dict()
        d['oneOf'] = self.oneOf

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a ChoiceMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): ChoiceMeta instance name
            d (dict): Serialised version of ChoiceMeta
        """

        description = d['description']
        oneOf = d['oneOf']
        enum_meta = ChoiceMeta(name, description, oneOf)

        return enum_meta
