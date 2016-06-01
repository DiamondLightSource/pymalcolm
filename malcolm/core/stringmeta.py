from malcolm.core.attributemeta import AttributeMeta


class StringMeta(AttributeMeta):
    """
    Meta object containing information for a string
    """

    def __init__(self, name, value):
        super(StringMeta, self).__init__(name=name)

        self.value = self.validate(value)

    def validate(self, value):
        """
        Check if given value is a string, or is castable to a string, and return the value.
        If it is not, raise a TypeError

        Args:
            value(str/int/float/long): Value to validate

        Returns:
            str: Value as a string

        """
        if isinstance(value, str):
            return value
        elif isinstance(value, (int, float, long)):  # TODO add any other types
            return str(value)
        else:
            raise TypeError("Value must be of type str or castable to str")
