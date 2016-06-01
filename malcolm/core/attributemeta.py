from loggable import Loggable


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
