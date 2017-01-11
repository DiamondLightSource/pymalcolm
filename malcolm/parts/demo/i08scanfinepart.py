from malcolm.core import method_takes
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart
from malcolm.controllers.runnablecontroller import RunnableController


class I08ScanFinePart(RunnableChildPart):
    def _get_midpoint(self, params, name="X"):
        # Make some very specific assumptions about the generator
	generators = params.generator.generators
        g = [g for g in generators if g.name[0] == "T1%sF" % name][0]
        mid = float(g.start[0] + g.stop[0]) / 2
        return mid

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        xp = self._get_midpoint(params, "X")
        yp = self._get_midpoint(params, "Y")
        xp += 0.0075 * yp
        yp += 0.0075 * xp
	fs = task.put_async(self.child["positionT1XC"], xp)
	fs += task.put_async(self.child["positionT1YC"], yp)
	task.wait_all(fs)
        super(I08ScanFinePart, self).configure(
            task, completed_steps, steps_to_do, part_info, params)

