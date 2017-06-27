from malcolm.core import Serializable, VMeta


@Serializable.register_subclass("malcolm:core/StringMeta:1.0")
class StringMeta(VMeta):
    """Meta object containing information for a string"""

    def validate(self, value):
        """Check if the value is None and returns "", else casts value to a
        string and returns it

        Args:
            value: Value to validate

        Returns:
            str: Value as a string [If value is not None]
        """

        if value is None:
            return ""
        else:
            return str(value)

    def doc_type_string(self):
        return "str"
