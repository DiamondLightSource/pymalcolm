from malcolm.core import Info


class ExportableInfo(Info):
    """Info about an exportable field name and object

    Args:
        name (str): Field name, e.g. "completedSteps"
        value (object): Object, e.g. Attribute() or Method()
        setter (function): The setter for an Attribute, or post function for
            a method
    """
    def __init__(self, name, value, setter):
        self.name = name
        self.value = value
        self.setter = setter
