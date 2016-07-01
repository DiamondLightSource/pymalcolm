from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register("malcolm:core/StringMeta:1.0")
class StringMeta(ScalarMeta):
    """Meta object containing information for a string"""

    def __init__(self, name, description):
        super(StringMeta, self).__init__(name=name, description=description)

    def validate(self, value):
        """
        Check if the value is None and returns None, else casts value to a
        string and returns it

        Args:
            value: Value to validate

        Returns:
            str: Value as a string [If value is not None]
        """

        if value is None:
            return None
        else:
            return str(value)
