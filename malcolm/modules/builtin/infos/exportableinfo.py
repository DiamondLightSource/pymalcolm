from malcolm.core import Info


class ExportableInfo(Info):
    """Info about an exportable field name and object

    Args:
        name (str): Field name, e.g. "completedSteps"
        mri (str): Block MRI, e.g. "BL18I-ML-STEP-06"
    """
    def __init__(self, name, mri):
        self.name = name
        self.mri = mri
