from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/StringMeta:1.0")
class StringMeta(VMeta):
    """Meta object containing information for a string"""

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