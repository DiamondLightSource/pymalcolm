from .serializable import Serializable
from .vmeta import VMeta


@Serializable.register_subclass("malcolm:core/HealthMeta:1.0")
class HealthMeta(VMeta):
    """Meta object containing information for a string"""
    _faults = None

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
            value = "OK"
        else:
            value = str(value)
        return value
