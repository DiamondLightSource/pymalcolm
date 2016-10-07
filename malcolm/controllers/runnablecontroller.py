from collections import OrderedDict

from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import RunnableStateMachine, REQUIRED, method_returns, \
    method_writeable_in, method_takes, ElementMap, Task, Hook
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta, StringArrayMeta


sm = RunnableStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []]


@sm.insert
@method_takes(
    "axesToMove", StringArrayMeta("Default value for configure() axesToMove"),
    []
)
class RunnableController(ManagerController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # Hooks
    Report = Hook()
    Validate = Hook()
    Configuring = Hook()
    PreRun = Hook()
    Running = Hook()
    PostRun = Hook()
    Aborting = Hook()

    # Attributes
    completed_steps = None
    configured_steps = None
    total_steps = None
    axes_to_move = None

    # Params passed to configure()
    configure_params = None

    # Stored for pause
    steps_per_run = 0

    @method_writeable_in(sm.IDLE)
    def edit(self):
        # Override edit to only work from Idle
        super(RunnableController, self).edit()

    @method_writeable_in(sm.FAULT, sm.DISABLED, sm.ABORTED, sm.READY)
    def reset(self):
        # Override reset to work from aborted and ready too
        super(RunnableController, self).reset()

    def create_attributes(self):
        for data in super(RunnableController, self).create_attributes():
            yield data
        self.completed_steps = NumberMeta(
            "int32", "Readback of number of scan steps").make_attribute(0)
        yield "completedSteps", self.completed_steps, None
        self.configured_steps = NumberMeta(
            "int32", "Number of steps currently configured").make_attribute(0)
        yield "configuredSteps", self.configured_steps, None
        self.total_steps = NumberMeta(
            "int32", "Readback of number of scan steps"
        ).make_attribute(0)
        yield "totalSteps", self.total_steps, None
        self.axes_to_move = StringArrayMeta(
            "Default axis names to scan for configure()"
        ).make_attribute(self.params.axesToMove)
        self.axes_to_move.meta.set_writeable_in(sm.EDITABLE)
        yield "axesToMove", self.axes_to_move, self.set_axes_to_move

    def do_reset(self):
        super(RunnableController, self).do_reset()
        self._update_configure_args()

    def _update_configure_args(self):
        # Look for all parts that hook into Configuring
        configure_funcs = self.Configuring.find_hooked_functions(self.parts)
        takes_elements = OrderedDict()
        defaults = OrderedDict()
        for part_name, func in configure_funcs.items():
            self.log_debug("Adding validating parameters from %s", part_name)
            takes_elements.update(func.MethodMeta.takes.elements.to_dict())
            defaults.update(func.MethodMeta.defaults)

        # Update takes with the things we need
        takes_elements.update(
            RunnableController.configure.MethodMeta.takes.elements.to_dict())
        takes = ElementMap(takes_elements)
        defaults["axesToMove"] = self.axes_to_move.value

        # Decorate validate and configure with the sum of its parts
        # No need to copy as the superclass _set_block_children does this
        self.block["validate"].takes.set_elements(takes)
        self.block["validate"].set_defaults(defaults)
        self.block["configure"].takes.set_elements(takes)
        self.block["configure"].set_defaults(defaults)

    def set_axes_to_move(self, value):
        self.axes_to_move.set_value(value)
        self._update_configure_args()

    @method_takes(*configure_args)
    @method_returns(
        "configureTime", NumberMeta("float64", "Estimated configure() time"),
        REQUIRED,
        "runTime", NumberMeta("float64", "Estimated run() time"), REQUIRED
    )
    def validate(self, params, returns):
        self.do_validate(params, returns)
        return params

    def do_validate(self, params, returns):
        raise NotImplementedError()

    @method_takes(*configure_args)
    @method_writeable_in(sm.IDLE)
    def configure(self, params):
        try:
            # Transition first so no-one else can run configure()
            self.transition(sm.CONFIGURING, "Configuring", create_tasks=True)

            # Store the params for use in seek()
            self.configure_params = params
            self.total_steps.set_value(params.generator.num)
            self.steps_per_run = self._get_steps_per_run(
                params.generator, params.axesToMove)

            # Do the actual configure
            self.do_configure(completed_steps=0, steps_to_do=self.steps_per_run)
            self.transition(sm.READY, "Done configuring")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Configuring")
            self.transition(sm.FAULT, str(e))
            raise

    def _get_steps_per_run(self, generator, axes_to_move):
        steps = 1
        axes_set = set(axes_to_move)
        for g in reversed(generator.generators):
            # If the axes_set is empty then we are done
            if not axes_set:
                break
            # Consume the axes that this generator scans
            for axis in g.position_units:
                assert axis in axes_set, \
                    "Axis %s is not in %s" % (axis, axes_to_move)
                axes_set.remove(axis)
            # Now multiply by the dimensions to get the number of steps
            for dim in g.index_dims:
                steps *= dim
        return steps

    def do_configure(self, completed_steps, steps_to_do):
        self.completed_steps.set_value(completed_steps)
        # Ask all parts to report relevant info and pass results to anyone
        # who cares
        part_info = self.run_hook(self.Report, self.part_tasks)
        self.run_hook(self.Configuring, self.part_tasks, completed_steps,
                      steps_to_do, part_info, **self.configure_params)
        self.configured_steps.set_value(completed_steps + steps_to_do)

    @method_writeable_in(sm.READY)
    def run(self):
        try:
            self.transition(sm.PRERUN, "Preparing for run")
            if self.configured_steps.value < self.total_steps.value:
                next_state = sm.READY
            else:
                next_state = sm.IDLE
            self._call_do_run()
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
            self.do_run()
        except StopIteration:
            # Work out if it was an abort or pause
            with self.lock:
                state = self.state.value
            self.log_debug("Do run got StopIteration from %s", state)
            if state in (sm.SEEKING, sm.PAUSED):
                # Wait to be restarted
                self.log_debug("Waiting for PreRun")
                task = Task("StateWaiter", self.process)
                task.when_matches(self.state, sm.PRERUN, [
                    sm.DISABLING, sm.ABORTING, sm.FAULT])
                # Restart it
                self.do_run()
            else:
                # just drop out
                self.log_debug("We were aborted")
                raise

    def do_run(self):
        self.run_hook(self.PreRun, self.part_tasks)
        self.transition(sm.RUNNING, "Waiting for scan to complete")
        self.run_hook(
            self.Running, self.part_tasks, self.update_completed_steps)
        self.transition(sm.POSTRUN, "Finishing run")
        completed_steps = self.configured_steps.value
        if completed_steps < self.total_steps.value:
            steps_to_do = self.steps_per_run
        else:
            steps_to_do = 0
        more_steps = steps_to_do > 0
        self.run_hook(self.PostRun, self.part_tasks, more_steps)
        if more_steps:
            self.do_configure(completed_steps, steps_to_do)

    def update_completed_steps(self, completed_steps):
        # TODO: this shows the maximum of all completed_steps, should be min
        if completed_steps > self.completed_steps.value:
            self.completed_steps.set_value(completed_steps)

    @method_writeable_in(
        sm.IDLE, sm.CONFIGURING, sm.READY, sm.PRERUN, sm.RUNNING, sm.POSTRUN,
        sm.RESETTING, sm.PAUSED, sm.SEEKING)
    def abort(self):
        try:
            self.transition(sm.ABORTING, "Aborting")
            self.do_abort()
            self.transition(sm.ABORTED, "Abort finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Aborting")
            self.transition(sm.FAULT, str(e))
            raise

    def do_abort(self, pause=False):
        for task in self.part_tasks.values():
            task.stop()
        self.run_hook(self.Aborting, self.create_part_tasks(), pause=pause)
        for task in self.part_tasks.values():
            task.wait()

    @method_writeable_in(sm.PRERUN, sm.RUNNING)
    def pause(self):
        try:
            self.transition(sm.SEEKING, "Seeking")
            self.do_abort(pause=True)
            self.part_tasks = self.create_part_tasks()
            self._reconfigure(self.completed_steps.value)
            self.transition(sm.PAUSED, "Pause finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Pausing")
            self.transition(sm.FAULT, str(e))
            raise

    def _reconfigure(self, completed_steps):
        steps_to_do = completed_steps % self.steps_per_run
        if steps_to_do == 0:
            steps_to_do = self.steps_per_run
        self.do_configure(completed_steps, steps_to_do)

    @method_writeable_in(sm.READY, sm.PAUSED)
    @method_takes("completedSteps", NumberMeta(
        "uint32", "Step to mark as the last completed step"), REQUIRED)
    def seek(self, params):
        completed_steps = params.completedSteps
        assert completed_steps >= 0, \
            "Cannot seek to before the start of the scan"
        assert completed_steps < self.total_steps.value, \
            "Cannot seek to after the end of the scan"
        try:
            self.transition(sm.SEEKING, "Seeking")
            self._reconfigure(completed_steps)
            self.transition(sm.PAUSED, "Seek finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Rewinding")
            self.transition(sm.FAULT, str(e))
            raise

    @method_writeable_in(sm.PAUSED)
    def resume(self):
        self.transition(sm.PRERUN, "Resuming run")





