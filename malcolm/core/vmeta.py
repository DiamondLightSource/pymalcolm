from malcolm.core.meta import Meta


class VMeta(Meta):
    """Abstract base class for Validating Meta objects"""

    def validate(self, value):
        """
        Abstract function to validate a given value

        Args:
            value(abstract): Value to validate
        """
        raise NotImplementedError(
            "Abstract validate function must be implemented in child classes")


