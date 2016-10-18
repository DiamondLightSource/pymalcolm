from collections import OrderedDict

from malcolm.core import method_takes, REQUIRED, Task, ElementMap, \
    RunnableStateMachine
from malcolm.core.vmetas import BooleanMeta
from malcolm.parts.builtin.layoutpart import LayoutPart
from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.ADCore.datasettablepart import DatasetProducedInfo


class RunnablePart(LayoutPart):
    # stored between runs
    run_future = None

    @RunnableController.Resetting
    def update_configure_args(self, task):
        # Wait until we are Idle
        if self.child.state == RunnableStateMachine.RESETTING:
            task.when_matches(self.child["state"], RunnableStateMachine.IDLE)
        else:
            if self.child["abort"].writeable:
                task.post(self.child["abort"])
            task.post(self.child["reset"])

        # Update our configure from our child
        takes_elements = OrderedDict()
        takes_elements.update(self.child["configure"].takes.elements.to_dict())
        takes = ElementMap(takes_elements)
        defaults = OrderedDict()
        defaults.update(self.child["configure"].defaults)

        # Decorate validate and configure with the sum of its parts
        self.method_metas["configure"].takes.set_elements(takes)
        self.method_metas["configure"].set_defaults(defaults)

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configuring
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        # configure the child and wait for completion
        if completed_steps == 0:
            # This is a configure from the start
            task.post(self.child["configure"], params)
            # TODO: this seems like it's in the wrong place...
            if "datasets" in self.child:
                return self._datasets_produced(self.child.datasets)
        else:
            # This is a seek to a position
            task.post(self.child["seek"], dict(completedSteps=completed_steps))

    def _datasets_produced(self, datasets_table):
        ret = []
        for i, dataset_name in enumerate(datasets_table.name):
            row = datasets_table[i]
            row[0] = "%s.%s" % (self.name, dataset_name)
            ret.append(DatasetProducedInfo(*row))
        return ret

    @RunnableController.Running
    @method_takes(
        "resume", BooleanMeta("Is this a resume?"), REQUIRED)
    def run(self, task, update_completed_steps, params):
        """Wait for run to finish
        Args:
            task (Task): The task helper
        """
        if params.resume:
            task.post(self.child["resume"])
        else:
            task.subscribe(self.child["completedSteps"], update_completed_steps)
            self.run_future = task.post_async(self.child["run"])
        task.wait_all(self.run_future)

    @RunnableController.Aborting
    @method_takes(
        "pause", BooleanMeta("Is this an abort for a pause?"), REQUIRED)
    def abort(self, task, params):
        if params.pause:
            task.post(self.child["pause"])
        elif self.child.state != RunnableStateMachine.RESETTING:
            task.post(self.child["abort"])

