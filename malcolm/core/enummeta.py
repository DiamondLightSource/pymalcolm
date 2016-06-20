from malcolm.core.attributemeta import AttributeMeta


class EnumMeta(AttributeMeta):
    """Meta object containing information for a enum"""

    def __init__(self, name, description, one_of):
        super(EnumMeta, self).__init__(name=name, description=description)

        self.one_of = one_of

    def set_one_of(self, one_of):
        """
        Set allowed values

        Args:
            one_of(list): List of allowed values
        """

        self.one_of = one_of

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

        if value in self.one_of:
            return value
        else:
            raise ValueError("%s is not a valid value" % value)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = super(EnumMeta, self).to_dict()
        d['one_of'] = self.one_of

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
        one_of = d['one_of']
        enum_meta = EnumMeta(name, description, one_of)

        return enum_meta

AttributeMeta.register_subclass(EnumMeta, "malcolm:core/Enum:1.0")
