from collections import OrderedDict

from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register("malcolm:core/ChoiceArrayMeta:1.0", "choices_list")
class ChoiceArrayMeta(ScalarMeta):
    """Meta object containing information for a choice array"""

    def __init__(self, name, description, choices_list):
        super(ChoiceArrayMeta, self).__init__(
            name, description, "choices_list")

        self.choices_list = choices_list  # A list of lists of choices

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
        if not hasattr(value, "__iter__"):
            raise ValueError("%s is not iterable" % value)

        for i, choice in enumerate(value):
            if choice is None:
                raise ValueError("Array elements can not be null")
            if choice not in self.choices_list[i]:
                raise ValueError("%s is not a valid value for element %s" %
                                 (choice, i))

        return value

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()
        d["typeid"] = self.typeid
        d["choices_list"] = self.choices_list
        d.update(super(ChoiceArrayMeta, self).to_dict())

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a ChoiceMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): ChoiceMeta instance name
            d (dict): Serialised version of ChoiceMeta
        """

        description = d['description']
        choices_list = d['choices_list']
        choice_array_meta = cls(name, description, choices_list)
        choice_array_meta.tags = d['tags']
        choice_array_meta.writeable = d['writeable']
        choice_array_meta.label = d['label']

        return choice_array_meta

