from malcolm.core import Part, REQUIRED, method_takes, method_returns
from malcolm.core.vmetas import StringMeta, NumberMeta, BooleanMeta
from malcolm.controllers.managercontroller import ManagerController, \
    layout_table_meta


@method_takes(
    "name", StringMeta("Name of the part"), REQUIRED,
    "child", StringMeta("Name of child object"), REQUIRED)
class LayoutPart(Part):
    # Child block object
    child = None
    mri = None
    name = None

    # Layout options
    x = 0
    y = 0
    visible = False

    def store_params(self, params):
        self.name = params.name
        self.child = self.process.get_block(params.child)
        self.mri = params.child

    @ManagerController.UpdateLayout
    @method_takes(
        "layout_table", layout_table_meta, REQUIRED)
    @method_returns(
        "mri", StringMeta("Malcolm full name of child block"), REQUIRED,
        "x", NumberMeta("float64", "X Co-ordinate of child block"), REQUIRED,
        "y", NumberMeta("float64", "X Co-ordinate of child block"), REQUIRED,
        "visible", BooleanMeta("Whether child block is visible"), REQUIRED)
    def update_layout_table(self, _, params, returns):
        for i, name in enumerate(params.layout_table.name):
            if name == self.name:
                _, _, self.x, self.y, self.visible = params.layout_table[i]
                # TODO: sever links here
        returns.mri = self.mri
        returns.x = self.x
        returns.y = self.y
        returns.visible = self.visible
        return returns
