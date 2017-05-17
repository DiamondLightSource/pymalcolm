from malcolm.compat import str_
from malcolm.core import Serializable, deserialize_object, VMeta, StringArray


@Serializable.register_subclass("malcolm:core/ChoiceMeta:1.0")
class ChoiceMeta(VMeta):
    """Meta object containing information for a enum"""

    endpoints = ["description", "choices", "tags", "writeable", "label"]

    def __init__(self, description="", choices=(), tags=(), writeable=False,
                 label=""):
        super(ChoiceMeta, self).__init__(description, tags, writeable, label)
        self.choices = self.set_choices(choices)

    def set_choices(self, choices):
        """Set the choices list"""
        choices = StringArray(deserialize_object(c, str_) for c in choices)
        # TODO: what if the value is no longer in the list?
        return self.set_endpoint_data("choices", choices)

    def validate(self, value):
        """Check if the value is valid returns it

        Args:
            value: Value to validate

        Returns:
            str: Value if it is valid
        Raises:
            exceptions.ValueError: If value not valid
        """
        if value is None:
            if self.choices:
                return self.choices[0]
            else:
                return ""
        elif value in self.choices:
            return value
        elif isinstance(value, int) and value < len(self.choices):
            return self.choices[value]
        else:
            raise ValueError(
                "%s is not a valid value in %s" % (value, self.choices))

    def doc_type_string(self):
        return " | ".join([repr(x) for x in self.choices])
