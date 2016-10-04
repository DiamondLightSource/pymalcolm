from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import NumberMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.managercontroller import ManagerController, \
    configure_args


class StatsPluginPart(LayoutPart):
    @ManagerController.Configuring
    @method_takes(
        "start_step", NumberMeta("uint32", "Step to start at"), REQUIRED,
        *configure_args)
    def configure(self, task, _):
        task.put({
            self.child["enableCallbacks"]: True,
            self.child["computeStatistics"]: True,
        })
