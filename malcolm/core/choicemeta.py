from malcolm.core.scalarmeta import ScalarMeta
from malcolm.core.serializable import Serializable


@Serializable.register("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(ScalarMeta):
    """Meta object containing information for a enum"""

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

        if value in self.choices:
            return value
        else:
            raise ValueError("%s is not a valid value" % value)

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = super(ChoiceMeta, self).to_dict()
        d["choices"] = self.choices
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
        choices = d['choices']
        choice_meta = cls(name, description, choices)

        return choice_meta
