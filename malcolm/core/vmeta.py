from malcolm.core.meta import Meta
from malcolm.compat import base_string


class VMeta(Meta):
    """Abstract base class for Scalar Meta objects"""

    endpoints = ["description", "tags", "writeable", "label"]

    def __init__(self, description="", tags=None, writeable=False, label=""):
        super(VMeta, self).__init__(description, tags)
        self.set_writeable(writeable)
        self.set_label(label)

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """
        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")

    def set_writeable(self, writeable, notify=True):
        """Set the writeable bool"""
        self.set_endpoint(bool, "writeable", writeable, notify)

    def set_label(self, label, notify=True):
        """Set the label string"""
        self.set_endpoint(base_string, "label", label, notify)
