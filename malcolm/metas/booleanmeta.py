from malcolm.metas.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
class BooleanMeta(ScalarMeta):
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
