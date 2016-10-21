from collections import OrderedDict

from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import RunnableStateMachine, REQUIRED, method_returns, \
    method_writeable_in, method_takes, ElementMap, Task, Hook, Info
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta, StringArrayMeta


class ProgressReportingInfo(Info):
    """This part will report progress via the update_completed_steps function
    passed at the Run hook"""
    pass

sm = RunnableStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []]


@method_takes(
    "axesToMove", StringArrayMeta("Default value for configure() axesToMove"),
    []
)
class RunnableController(ManagerController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # The stateMachine that this controller implements
    stateMachine = sm

    Validate = Hook()
    """Called at validate() to check parameters are valid

    Args:
        task (Task): The task used to perform operations on child blocks
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part validate()
            method_takes() decorator
    """

    ReportStatus = Hook()
    """Called before Validate, Configure, PostRunReady and Seek hooks to report
    the current configuration of all parts

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [Info]: any configuration Info relevant to other parts
    """

    Configure = Hook()
    """Called at configure() to configure child block for a run

    Args:
        task (Task): The task used to perform operations on child blocks
        completed_steps (int): Number of steps already completed
        steps_to_do (int): Number of steps we should configure for
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part configure()
            method_takes() decorator

    Returns:
        [Info]: ProgressReportingInfo if this part will report progress in
            the Run hook, plus any configuration Info that needs to be passed to
            other parts for storing in attributes
    """

    PostConfigure = Hook()
    """Called at the end of configure() to store configuration info calculated
     in the Configure hook

    Args:
        task (Task): The task used to perform operations on child blocks
        part_info (dict): {part_name: [Info]} returned from Configure hook
    """

    Run = Hook()
    """Called at run() to start the configured steps running

    Args:
        task (Task): The task used to perform operations on child blocks
        update_completed_steps (func): If ProgressReportingInfo has been
            returned from Configure hook, then this part should call
            update_completed_steps(completed_steps) with the integer step
            value each time progress is updated
    """

    PostRunReady = Hook()
    """Called at the end of run() when there are more steps to be run

    Args:
        task (Task): The task used to perform operations on child blocks
        completed_steps (int): Number of steps already completed
        steps_to_do (int): Number of steps we should configure for
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part configure()
            method_takes() decorator
    """

    PostRunIdle = Hook()
    """Called at the end of run() when there are no more steps to be run

    Args:
        task (Task): The task used to perform operations on child blocks
    """

    Pause = Hook()
    """Called at pause() to pause the current scan before Seek is called

    Args:
        task (Task): The task used to perform operations on child blocks
    """

    Seek = Hook()
    """Called at seek() or at the end of pause() to reconfigure for a different
    number of completed_steps

    Args:
        task (Task): The task used to perform operations on child blocks
        completed_steps (int): Number of steps already completed
        steps_to_do (int): Number of steps we should configure for
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part configure()
            method_takes() decorator
    """

    Resume = Hook()
    """Called at resume() to continue a paused scan

    Args:
        task (Task): The task used to perform operations on child blocks
        update_completed_steps (func): If ProgressReportingInfo has been
            returned from Configure hook, then this part should call
            update_completed_steps(completed_steps) with the integer step
            value each time progress is updated
    """

    Abort = Hook()
    """Called at abort() to stop the current scan

    Args:
        task (Task): The task used to perform operations on child blocks
    """

    # Attributes
    completed_steps = None
    configured_steps = None
    total_steps = None
    axes_to_move = None

    # Params passed to configure()
    configure_params = None

    # Stored for pause
    steps_per_run = 0

    # Progress reporting parts
    progress_reporting = None

    def go_to_error_state(self, exception):
        if isinstance(exception, StopIteration):
            # Don't need to transition to aborted, we're already there
            self.log_warning("Abort occurred while running stateful function")
        else:
            super(RunnableController, self).go_to_error_state(exception)

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
        # Look for all parts that hook into Configure
        configure_funcs = self.Configure.find_hooked_functions(self.parts)
        takes_elements = OrderedDict()
        defaults = OrderedDict()
        for part_name, func_name in configure_funcs.items():
            self.log_debug("Adding validating parameters from %s.%s",
                           part_name, func_name)
            method_meta = self.parts[part_name].method_metas[func_name]
            takes_elements.update(method_meta.takes.elements.to_dict())
            defaults.update(method_meta.defaults)

        # Update takes with the things we need
        takes_elements.update(
            RunnableController.configure.MethodMeta.takes.elements.to_dict())
        takes = ElementMap(takes_elements)
        defaults["axesToMove"] = self.axes_to_move.value

        # Decorate validate and configure with the sum of its parts
        # No need to copy as the superclass create_methods() does this
        self.block["validate"].takes.set_elements(takes)
        self.block["validate"].set_defaults(defaults)
        self.block["configure"].takes.set_elements(takes)
        self.block["configure"].set_defaults(defaults)

    def set_axes_to_move(self, value):
        self.axes_to_move.set_value(value)
        self._update_configure_args()

    @method_takes(*configure_args)
    def validate(self, params):
        self.do_validate(params)

    def do_validate(self, params):
        # Make some tasks just for validate
        part_tasks = self.create_part_tasks()
        # Get any status from all parts
        part_info = self.run_hook(self.ReportStatus, part_tasks)
        # Validate the params with all the parts
        self.run_hook(self.Validate, part_tasks, part_info, params)

    @method_takes(*configure_args)
    @method_writeable_in(sm.IDLE)
    def configure(self, params):
        self.try_stateful_function(
            sm.CONFIGURING, sm.READY, self.do_configure, params)

    def do_configure(self, params):
        # These are the part tasks that abort() and pause() will operate on
        self.part_tasks = self.create_part_tasks()
        # Store the params for use in seek()
        self.configure_params = params
        # Set the steps attributes that we will do across many run() calls
        self.total_steps.set_value(params.generator.num)
        self.completed_steps.set_value(0)
        self.configured_steps.set_value(0)
        # TODO: this should come from tne generator
        self.steps_per_run = self._get_steps_per_run(
            params.generator, params.axesToMove)
        # Get any status from all parts
        part_info = self.run_hook(self.ReportStatus, self.part_tasks)
        # Use the ProgressReporting classes for ourselves
        self.progress_reporting = list(ProgressReportingInfo.filter(part_info))
        # Run the configure command on all parts, passing them info from
        # ReportStatus. Parts should return any reporting info for PostConfigure
        completed_steps = 0
        steps_to_do = self.steps_per_run
        part_info = self.run_hook(
            self.Configure, self.part_tasks, completed_steps, steps_to_do,
            part_info, **self.configure_params)
        # Take configuration info and reflect it as attribute updates
        self.run_hook(self.PostConfigure, self.part_tasks, part_info)
        # Update the completed and configured steps
        self.configured_steps.set_value(steps_to_do)

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

    @method_writeable_in(sm.READY)
    def run(self):
        if self.configured_steps.value < self.total_steps.value:
            next_state = sm.READY
        else:
            next_state = sm.IDLE
        self.try_stateful_function(sm.RUNNING, next_state, self._call_do_run)

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
                bad_states = [sm.DISABLING, sm.ABORTING, sm.FAULT]
                task.when_matches(self.state, sm.RUNNING, bad_states)
                # Restart it

                self.do_run(resume=True)
            else:
                # just drop out
                self.log_debug("We were aborted")
                raise

    def do_run(self, resume=False):
        self.run_hook(self.PreRun, self.part_tasks)
        self.transition(sm.RUNNING, "Waiting for scan to complete")
        self.run_hook(
            self.Run, self.part_tasks, self.update_completed_steps,
            resume=resume)
        self.transition(sm.POSTRUN, "Finishing run")
        completed_steps = self.configured_steps.value
        if completed_steps < self.total_steps.value:
            steps_to_do = self.steps_per_run
        else:
            steps_to_do = 0
        more_steps = steps_to_do > 0
        self.run_hook(self.PostRunReady, self.part_tasks, more_steps)
        if more_steps:
            self.do_configure(completed_steps, steps_to_do)

    def update_completed_steps(self, completed_steps):
        # TODO: this shows the maximum of all completed_steps, should be min
        if completed_steps > self.completed_steps.value:
            self.completed_steps.set_value(completed_steps)

    @method_writeable_in(
        sm.IDLE, sm.CONFIGURING, sm.READY, sm.RUNNING, sm.POSTRUN, sm.RESETTING,
        sm.PAUSED, sm.SEEKING)
    def abort(self):
        try:
            self.transition(sm.ABORTING, "Abort")
            self.do_abort()
            self.transition(sm.ABORTED, "Abort finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Abort")
            self.transition(sm.FAULT, str(e))
            raise

    def do_abort(self, pause=False):
        for task in self.part_tasks.values():
            task.stop()
        self.run_hook(self.Abort, self.create_part_tasks(), pause=pause)
        for task in self.part_tasks.values():
            task.wait()

    @method_writeable_in(sm.RUNNING)
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
        self.transition(sm.RUNNING, "Resuming run")





