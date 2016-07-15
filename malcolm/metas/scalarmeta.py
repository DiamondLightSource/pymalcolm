from collections import OrderedDict

from malcolm.core.meta import Meta


class ScalarMeta(Meta):
    """Abstract base class for Scalar Meta objects"""

    endpoints = ["description", "tags", "writeable", "label"]

    def __init__(self, name, description, *args):
        super(ScalarMeta, self).__init__(name, description, *args)
        self.writeable = True
        self.label = name

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """

        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")

    def set_writeable(self, writeable, notify=True):
        self.writeable = writeable
        self.on_changed([["writeable"], writeable], notify)

    def set_label(self, label, notify=True):
        self.label = label
        self.on_changed([["label"], label], notify)

    @classmethod
    def from_dict(cls, name, d, *args):
        """Create a ScalarMeta subclass instance from the serialized version
        of itself

        Args:
            name (str): ScalarMeta instance name
            d (dict): Something that self.to_dict() would create
        """
        meta = cls(name, d["description"], *args)
        meta.writeable = d["writeable"]
        meta.tags = d["tags"]
        meta.label = d["label"]
        return meta
