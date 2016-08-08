from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta


@Serializable.register_subclass("malcolm:core/StringArrayMeta:1.0")
class StringArrayMeta(VArrayMeta):
    """Meta object containing information for a string array"""

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to strings

        Args:
            value (iterable): value to be validated

        Returns:
            List of Strings or None if value is None
        """
        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueError("%r is not a list" % (value,))

        validated = [str(x) if x is not None else None for x in value]

        if None in validated:
            raise ValueError("Array elements can not be null")

        return validated