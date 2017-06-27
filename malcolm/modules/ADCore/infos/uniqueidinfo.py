from malcolm.core import Info


class UniqueIdInfo(Info):
    """Report the current value of the UniqueId array counter"""
    def __init__(self, value):
        self.value = value
