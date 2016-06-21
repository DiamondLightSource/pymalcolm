from malcolm.core.attributemeta import AttributeMeta


@AttributeMeta.register_subclass("malcolm:core/Enum:1.0")
class EnumMeta(AttributeMeta):
    """Meta object containing information for a enum"""

    def __init__(self, name, description, oneOf):
        super(EnumMeta, self).__init__(name=name, description=description)

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

        d = super(EnumMeta, self).to_dict()
        d['oneOf'] = self.oneOf

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a EnumMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): EnumMeta instance name
            d (dict): Serialised version of EnumMeta
        """

        description = d['description']
        oneOf = d['oneOf']
        enum_meta = EnumMeta(name, description, oneOf)

        return enum_meta

AttributeMeta.register_subclass(EnumMeta, "malcolm:core/Enum:1.0")
