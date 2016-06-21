from malcolm.core.attributemeta import AttributeMeta


@AttributeMeta.register_subclass("malcolm:core/Boolean:1.0")
class BooleanMeta(AttributeMeta):
    """Meta object containing information for a boolean"""

    def __init__(self, name, description):
        super(BooleanMeta, self).__init__(name=name, description=description)

    def validate(self, value):
        """
        Check if the value is None and returns None, else casts value to a
        boolean and returns it

        Args:
            value: Value to validate

        Returns:
            bool: Value as a boolean [If value is not None]
        """

        if value is None:
            return None
        else:
            return bool(value)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = super(BooleanMeta, self).to_dict()

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a BooleanMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): BooleanMeta instance name
            d (dict): Serialised version of BooleanMeta
        """

        boolean_meta = BooleanMeta(name, d["description"])

        return boolean_meta

AttributeMeta.register_subclass(BooleanMeta, "malcolm:core/Boolean:1.0")
