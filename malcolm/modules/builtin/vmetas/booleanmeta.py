from malcolm.core import Serializable, VMeta


@Serializable.register_subclass("malcolm:core/BooleanMeta:1.0")
class BooleanMeta(VMeta):
    """Meta object containing information for a boolean"""

    def validate(self, value):
        """Cast value to boolean and return it

        Args:
            value: Value to validate

        Returns:
            bool: Value as a boolean
        """
        return bool(value)

    def doc_type_string(self):
        return "bool"
