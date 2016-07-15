from collections import OrderedDict

from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(ScalarMeta):
    """Meta object containing information for a enum"""

    endpoints = ["choices", "description", "tags", "writeable", "label"]

    def __init__(self, name, description, choices):
        super(ChoiceMeta, self).__init__(name=name, description=description)

        self.choices = choices

    def set_choices(self, choices):
        """
        Set allowed values

        Args:
            choices (list): List of allowed values
        """

        self.choices = choices

    def validate(self, value):
        """
        Check if the value is valid returns it

        Args:
            value: Value to validate

        Returns:
            Value if it is valid
        Raises:
            ValueError: If value not valid
        """

        if value is None or value in self.choices:
            return value
        else:
            raise ValueError(
                "%s is not a valid value in %s" % (value, self.choices))

    @classmethod
    def from_dict(cls, name, d):
        """Create a ChoiceMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): ChoiceMeta instance name
            d (dict): Serialised version of ChoiceMeta
        """

        description = d['description']
        choices = d['choices']
        choice_meta = cls(name, description, choices)
        choice_meta.tags = d['tags']
        choice_meta.writeable = d['writeable']
        choice_meta.label = d['label']

        return choice_meta
