from malcolm.core import Info


class ModifiedInfo(Info):
    """Info about an exportable field name and object

    Args:
        name (str): Field name, e.g. "completedSteps"
        original_value: Original saved/loaded value
        current_value: Current value
    """
    def __init__(self, name, original_value, current_value):
        self.name = name
        self.original_value = original_value
        self.current_value = current_value
