from collections import OrderedDict

import numpy as np

from malcolm.core import RunnableDeviceStateMachine, REQUIRED, method_returns, \
    method_only_in, method_takes, ElementMap, Attribute, Task, Hook
from malcolm.core.vmetas import PointGeneratorMeta, StringArrayMeta, NumberMeta
from malcolm.controllers.builtin.defaultcontroller import DefaultController


sm = RunnableDeviceStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axes_to_move", StringArrayMeta("Axes that should be moved"), REQUIRED,
    "exposure", NumberMeta("float64", "How long to remain at each point"),
    REQUIRED]


@sm.insert
@method_takes()
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # hooks
    Aborting = Hook()
    # default attributes
    totalSteps = None
    # For storing iterator
    iterator = None
    points = None
    # Params passed to configure()
    configure_params = None

    def get_point(self, num):
        npoints = len(self.points)
        if num >= npoints:
            # Generate some more points and cache them
            for i in range(num - npoints + 1):
                self.points.append(next(self.iterator))
        return self.points[num]

    def create_attributes(self):
        self.totalSteps = Attribute(NumberMeta(
            "int32", "Readback of number of scan steps"), 0)
        yield "totalSteps", self.totalSteps, None

    def something_create_methods(self):
        # Look for all parts that hook into the validate method
        validate_funcs = self.Validating.find_hooked_functions(self.parts)
        takes_elements = OrderedDict()
        defaults = OrderedDict()
        for part_name, func in validate_funcs.items():
            self.log_debug("Adding validating parameters from %s", part_name)
            takes_elements.update(func.MethodMeta.takes.to_dict())
            defaults.update(func.MethodMeta.defaults)
        takes = ElementMap(takes_elements)

        # Decorate validate and configure with the sum of its parts
        # No need to copy as the superclass _set_block_children does this
        self.validate.MethodMeta.set_takes(takes)
        self.validate.MethodMeta.set_returns(takes)
        self.validate.MethodMeta.set_defaults(defaults)
        self.configure.MethodMeta.set_takes(takes)
        self.validate.MethodMeta.set_defaults(defaults)

        return super(ManagerController, self).create_methods()

    @method_takes(*configure_args)
    @method_returns(*configure_args)
    def validate(self, params, _):
        self.do_validate(params)
        return params

    def do_validate(self, params):
        raise NotImplementedError()

    @method_only_in(sm.IDLE)
    @method_takes(*configure_args)
    def configure(self, params):
        try:
            self.transition(sm.CONFIGURING, "Configuring", create_tasks=True)
            self.configure_params = params
            self.points = []
            self.iterator = params.generator.iterator()
            steps = np.prod(params.generator.index_dims)
            self.totalSteps.set_value(steps)
            self.block["completedSteps"].set_value(0)
            self.do_configure(self.part_tasks, params)
            self.transition(sm.READY, "Done configuring")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Configuring")
            self.transition(sm.FAULT, str(e))
            raise

    def do_configure(self, part_tasks, params, start_index=0):
        raise NotImplementedError()

    @method_only_in(sm.READY)
    def run(self):
        try:
            self.transition(sm.PRERUN, "Preparing for run", create_tasks=True)
            next_state = self._call_do_run()
            self.transition(next_state, "Run finished")
        except StopIteration:
            self.log_warning("Run aborted")
            raise
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Running")
            self.transition(sm.FAULT, str(e))
            raise

    def _call_do_run(self):
        try:
            return self.do_run(self.part_tasks)
        except StopIteration:
            # Work out if it was an abort or pause
            with self.lock:
                state = self.state.value
            self.log_debug("Do run got StopIteration from %s", state)
            if state in (sm.REWINDING, sm.PAUSED):
                # Wait to be restarted
                self.log_debug("Waiting for PreRun")
                task = Task("StateWaiter", self.process)
                futures = task.when_matches(self.state, sm.PRERUN, [
                    sm.DISABLING, sm.ABORTING, sm.FAULT])
                task.wait_all(futures)
                # Restart it
                return self._call_do_run()
            else:
                # just drop out
                self.log_debug("We were aborted")
                raise

    def do_run(self, part_tasks):
        raise NotImplementedError()

    @method_only_in(sm.IDLE, sm.CONFIGURING, sm.READY, sm.PRERUN, sm.RUNNING,
                    sm.POSTRUN, sm.RESETTING, sm.PAUSED, sm.REWINDING)
    def abort(self):
        try:
            self.transition(sm.ABORTING, "Aborting")
            self.do_abort()
            self.transition(sm.ABORTED, "Abort finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Aborting")
            self.transition(sm.FAULT, str(e))
            raise

    def do_abort(self):
        for task in self.part_tasks.values():
            task.stop()
        self.run_hook(self.Aborting, self.create_part_tasks())
        for task in self.part_tasks.values():
            task.wait()

    @method_only_in(sm.PRERUN, sm.RUNNING)
    def pause(self):
        try:
            self.transition(sm.REWINDING, "Rewinding")
            current_index = self.block.completedSteps
            self.do_abort()
            self.part_tasks = self.create_part_tasks()
            self.do_configure(
                self.part_tasks, self.configure_params, current_index)
            self.transition(sm.PAUSED, "Pause finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Pausing")
            self.transition(sm.FAULT, str(e))
            raise

    @method_only_in(sm.READY, sm.PAUSED)
    @method_takes("steps", NumberMeta(
        "uint32", "Number of steps to rewind"), REQUIRED)
    def rewind(self, params):
        current_index = self.block.completedSteps
        requested_index = current_index - params.steps
        assert requested_index >= 0, \
            "Cannot retrace to before the start of the scan"
        try:
            self.transition(sm.REWINDING, "Rewinding")
            self.block["completedSteps"].set_value(requested_index)
            self.do_configure(
                self.part_tasks, self.configure_params, requested_index)
            self.transition(sm.PAUSED, "Rewind finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Rewinding")
            self.transition(sm.FAULT, str(e))
            raise

    @method_only_in(sm.PAUSED)
    def resume(self):
        self.transition(sm.PRERUN, "Resuming run")





