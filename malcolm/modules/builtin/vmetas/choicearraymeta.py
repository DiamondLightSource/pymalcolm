from malcolm.compat import str_
from malcolm.core import Serializable, StringArray, VArrayMeta
from .choicemeta import ChoiceMeta


@Serializable.register_subclass("malcolm:core/ChoiceArrayMeta:1.0")
class ChoiceArrayMeta(ChoiceMeta, VArrayMeta):
    """Meta object containing information for a choice array"""

    def validate(self, value):
        """Verify value can be iterated and cast elements to choices

        Args:
            value (list): Value to be validated

        Returns:
            StringArray: The validated value
        """
        if value is None:
            return StringArray()
        elif isinstance(value, str_):
            raise ValueError("Expected iterable of strings, got %r" % value)
        else:
            for i, choice in enumerate(value):
                if choice not in self.choices:
                    raise ValueError("%s is not a valid value for element %s" %
                                     (choice, i))
            return StringArray(value)

    def doc_type_string(self):
        return "[%s]" % super(ChoiceArrayMeta, self).doc_type_string()
