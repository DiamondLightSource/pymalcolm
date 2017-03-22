from malcolm.core import Info


class ParameterTweakInfo(Info):
    """Tweaks"""
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value
