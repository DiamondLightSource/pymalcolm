from malcolm.core import method_takes, REQUIRED
from malcolm.core.vmetas import NumberMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.managercontroller import ManagerController, \
    configure_args


class SimDetectorDriverPart(LayoutPart):
    @ManagerController.Configuring
    @method_takes(
        "start_step", NumberMeta("uint32", "Step to start at"), REQUIRED,
        *configure_args)
    def configure(self, task, params):
        task.put({
            self.child["exposure"]: params.exposure,
            self.child["imageMode"]: "Multiple",
            self.child["numImages"]: params.generator.num,
            self.child["arrayCounter"]: params.start_step,
            self.child["arrayCallbacks"]: True,
        })

    @ManagerController.Running
    def run(self, task):
        task.post(self.child["start"])

    @ManagerController.Aborting
    def abort(self, task):
        task.post(self.child["stop"])
