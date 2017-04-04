from scanpointgenerator import LineGenerator, SpiralGenerator

from malcolm.core import method_takes
from malcolm.parts.scanning import RunnableChildPart
from malcolm.controllers.scanning import RunnableController


class BL08IScanCombinedPart(RunnableChildPart):
    def _get_range(self, params, name="X"):
        # Make some very specific assumptions about the generator
        search_name = "Sample%s" % name
        for g in params.generator.generators:
            if isinstance(g, LineGenerator):
                if search_name in g.name:
                    i = g.name.index(search_name)
                    return g.start[i], g.stop[i]
            elif isinstance(g, SpiralGenerator):
                if search_name in g.names:
                    i = g.names.index(search_name)
                    return g.centre[i] - g.radius, g.centre[i] + g.radius
        current = self.child["positionT1%sC" % name].value
        return current, current

    # MethodMeta will be filled in by _update_configure_args
    @RunnableController.Configure
    @method_takes()
    def configure(self, task, completed_steps, steps_to_do, part_info, params):
        xstart, xstop = self._get_range(params, "X")
        ystart, ystop = self._get_range(params, "Y")
        if abs(xstart - xstop) > 0.04 or abs(ystart - ystop) > 0.04:
            # outside the range of the piezo, do a combined scan
            task.put(self.child["fineMode"], 0)
        else:
            # inside the range of piezo, just move fine
            task.put(self.child["fineMode"], 1)
            # move to corrected centre of range
            xp = (xstop + xstart) / 2.0
            yp = (ystop + ystart) / 2.0
            xp += 0.0075 * yp
            yp += 0.0075 * xp
        fs = task.put_async(self.child["positionT1XC"], xp)
        fs += task.put_async(self.child["positionT1YC"], yp)
        task.wait_all(fs)
        super(BL08IScanCombinedPart, self).configure(
            task, completed_steps, steps_to_do, part_info, params)

