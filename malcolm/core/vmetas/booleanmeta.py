from malcolm.core.serializable import Serializable
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
class BooleanMeta(VMeta):
    """Meta object containing information for a boolean"""

    def validate(self, value):
        """
        Check if the value is None and returns None, else casts value to a
        boolean and returns it

        Args:
            value: Value to validate

        Returns:
            bool: Value as a boolean [If value is not None]
        """

        return bool(value)
