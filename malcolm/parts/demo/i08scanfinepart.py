from malcolm.core import method_takes
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.controllers.runnablecontroller import RunnableController


class I08ScanFinePart(RunnableChildPart):
    def _goto_midpoint(self, task, params, name="X"):
        # Make some very specific assumptions about the generator
	generators = params.generator.generators
        g = [g for g in generators if g.name[0] == "T1%sF" % name][0]
        mid = float(g.start[0] + g.stop[0]) / 2
	futures = task.put_async(self.child["positionT1%sC" % name], mid)
	return futures

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
	fs = self._goto_midpoint(task, params, "X")
	fs += self._goto_midpoint(task, params, "Y")
	task.wait_all(fs)
	task.sleep(1)
        super(I08ScanFinePart, self).configure(
            task, completed_steps, steps_to_do, part_info, params)

