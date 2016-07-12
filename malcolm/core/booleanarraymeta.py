from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/BooleanArrayMeta:1.0")
class BooleanArrayMeta(ScalarMeta):
    """Meta object containing information for a boolean array"""

    def __init__(self, name, description):
        super(BooleanArrayMeta, self).__init__(
            name=name, description=description)

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to boolean

        Args:
            value (iterable): value to be validated

        Returns:
            List of Booleans or None if value is None
        """
        if value is None:
            return None
        if not hasattr(value, "__iter__"):
            raise ValueError("%s is not iterable" % value)
        validated = [bool(x) if x is not None else None for x in value]
        if None in validated:
            raise ValueError("Array elements can not be null")
        return validated

