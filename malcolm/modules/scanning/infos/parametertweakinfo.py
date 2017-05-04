from malcolm.core import Info


class ParameterTweakInfo(Info):
    """Info about a configure() parameter that needs to be tweaked

    Args:
        parameter (str): Parameter name, e.g. "generator"
        value: The value it should be changed to
    """
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
