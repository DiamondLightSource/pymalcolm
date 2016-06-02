from malcolm.core.loggable import Loggable
from collections import OrderedDict


class AttributeMeta(Loggable):
    """Abstract base class for Meta objects"""

    def __init__(self, name):
        super(AttributeMeta, self).__init__(logger_name=name)
        self.name = name

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """

        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()
        # Will add description here once it exists

        return d
