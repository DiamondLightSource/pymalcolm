from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta
from malcolm.core.vmetas.choicemeta import ChoiceMeta


@Serializable.register_subclass("malcolm:core/ChoiceArrayMeta:1.0")
class ChoiceArrayMeta(ChoiceMeta, VArrayMeta):
    """Meta object containing information for a choice array"""

    def validate(self, value):
        """
        Verify value can be iterated and cast elements to choices

        Args:
            value(iterable): Value to be validated

        Returns:
            List of Choices or None if value is None
        """

        if value is None:
            return None

        if not isinstance(value, list):
            raise ValueError("%r is not a list" % (value,))

        for i, choice in enumerate(value):
            if choice is None:
                raise ValueError("Array elements can not be null")
            if choice not in self.choices:
                raise ValueError("%s is not a valid value for element %s" %
                                 (choice, i))

        return value