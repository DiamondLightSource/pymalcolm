from malcolm.metas.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(ScalarMeta):
    """Meta object containing information for a enum"""

    endpoints = ["description", "choices", "tags", "writeable", "label"]

    def __init__(self, description="", choices=None, tags=None, writeable=False,
                 label=""):
        super(ChoiceMeta, self).__init__(description, tags, writeable, label)
        if choices is None:
            choices = []
        self.set_choices(choices)

    def set_choices(self, choices, notify=True):
        """Set the choices list"""
        self.set_endpoint([base_string], "choices", choices, notify)

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
        elif isinstance(value, int) and value < len(self.choices):
            return value
        else:
            raise ValueError(
                "%s is not a valid value in %s" % (value, self.choices))
