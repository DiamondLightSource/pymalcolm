from malcolm.core import Info


class LayoutInfo(Info):
    """Info about the position and visibility of a child block in a layout

    Args:
        mri (str): Malcolm full name of child block
        x (float): X Coordinate of child block
        y (float): Y Coordinate of child block
        visible (bool): Whether child block is visible
    """
    def __init__(self, mri, x, y, visible):
        self.mri = mri
        self.x = x
        self.y = y
        self.visible = visible
