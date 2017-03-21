from malcolm.controllers.managercontroller import ManagerController
from malcolm.core import RunnableStateMachine, REQUIRED, method_also_takes, \
    method_writeable_in, method_takes, MethodMeta, Task, Hook, method_returns, \
    Info, AbortedError, BadValueError
from malcolm.core.vmetas import PointGeneratorMeta, NumberMeta, StringArrayMeta


class ParameterTweakInfo(Info):
    """Tweaks"""
    def __init__(self, parameter, value):
        self.parameter = parameter
        self.value = value


sm = RunnableStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []]


@method_also_takes(
    "axesToMove", StringArrayMeta("Default value for configure() axesToMove"),
    []
)
class RunnableController(ManagerController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # The stateMachine that this controller implements
    stateMachine = sm()

    Validate = Hook()
    """Called at validate() to check parameters are valid

    Args:
        task (Task): The task used to perform operations on child blocks
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part validate()
            method_takes() decorator

    Returns:
        [`ParameterTweakInfo`] - any parameters tweaks that have occurred
            to make them compatible with this part. If any are returned,
            Validate will be re-run with the modified parameters.
    """

    ReportStatus = Hook()
    """Called before Validate, Configure, PostRunReady and Seek hooks to report
    the current configuration of all parts

    Args:
        task (Task): The task used to perform operations on child blocks

    Returns:
        [`Info`] - any configuration Info objects relevant to other parts
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
        [`Info`] - any Info objects that need to be passed to other parts for
            storing in attributes
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
        update_completed_steps (callable): If part can report progress, this
            part should call update_completed_steps(completed_steps, self) with
            the integer step value each time progress is updated
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
        update_completed_steps (callable): If part can report progress, this
            part should call update_completed_steps(completed_steps, self) with
            the integer step value each time progress is updated
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

    # Progress reporting dict
    # {part: completed_steps for that part}
    progress_reporting = None

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
        self.completed_steps.meta.set_writeable_in(sm.PAUSED, sm.READY)
        yield "completedSteps", self.completed_steps, self.set_completed_steps
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
        self.configured_steps.set_value(0)
        self.completed_steps.set_value(0)
        self.total_steps.set_value(0)

    def go_to_error_state(self, exception):
        if isinstance(exception, AbortedError):
            self.log_info("Got AbortedError in %s" % self.state.value)
        else:
            super(RunnableController, self).go_to_error_state(exception)

    def _update_configure_args(self):
        # Look for all parts that hook into Configure
        configure_funcs = self.Configure.find_hooked_functions(self.parts)
        method_metas = []
        for part, func_name in configure_funcs.items():
            method_metas.append(part.method_metas[func_name])

        # Update takes with the things we need
        default_configure = MethodMeta.from_dict(
            RunnableController.configure.MethodMeta.to_dict())
        default_configure.defaults["axesToMove"] = self.axes_to_move.value
        method_metas.append(default_configure)

        # Decorate validate and configure with the sum of its parts
        self.block["validate"].recreate_from_others(method_metas)
        self.block["validate"].set_returns(self.block["validate"].takes)
        self.block["configure"].recreate_from_others(method_metas)

    def set_axes_to_move(self, value):
        self.axes_to_move.set_value(value)
        self._update_configure_args()

    @method_takes(*configure_args)
    def validate(self, params, returns):
        iterations = 10
        # Make some tasks just for validate
        part_tasks = self.create_part_tasks()
        # Get any status from all parts
        status_part_info = self.run_hook(self.ReportStatus, part_tasks)
        while iterations > 0:
            # Try up to 10 times to get a valid set of parameters
            iterations -= 1
            # Validate the params with all the parts
            validate_part_info = self.run_hook(
                self.Validate, part_tasks, status_part_info, **params)
            tweaks = ParameterTweakInfo.filter_values(validate_part_info)
            if tweaks:
                for tweak in tweaks:
                    params[tweak.parameter] = tweak.value
                    self.log_debug(
                        "Tweaking %s to %s", tweak.parameter, tweak.value)
            else:
                # Consistent set, just return the params
                return params
        raise ValueError("Could not get a consistent set of parameters")

    @method_takes(*configure_args)
    @method_writeable_in(sm.IDLE)
    def configure(self, params):
        """Configure for a scan"""
        self.validate(params, params)
        self.try_stateful_function(
            sm.CONFIGURING, sm.READY, self.do_configure, params)

    def do_configure(self, params):
        # These are the part tasks that abort() and pause() will operate on
        self.part_tasks = self.create_part_tasks()
        # Load the saved settings first
        self.run_hook(self.Load, self.part_tasks, self.load_structure)
        # Store the params for use in seek()
        self.configure_params = params
        # This will calculate what we need from the generator, possibly a long
        # call
        params.generator.prepare()
        # Set the steps attributes that we will do across many run() calls
        self.total_steps.set_value(params.generator.size)
        self.completed_steps.set_value(0)
        self.configured_steps.set_value(0)
        # TODO: We can be cleverer about this and support a different number
        # of steps per run for each run by examining the generator structure
        self.steps_per_run = self._get_steps_per_run(
            params.generator, params.axesToMove)
        # Get any status from all parts
        part_info = self.run_hook(self.ReportStatus, self.part_tasks)
        # Use the ProgressReporting classes for ourselves
        self.progress_reporting = {}
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
        for dim in reversed(generator.dimensions):
            # If the axes_set is empty then we are done
            if not axes_set:
                break
            # Consume the axes that this generator scans
            for axis in dim.axes:
                assert axis in axes_set, \
                    "Axis %s is not in %s" % (axis, axes_to_move)
                axes_set.remove(axis)
            # Now multiply by the dimensions to get the number of steps
            steps *= dim.size
        return steps

    @method_writeable_in(sm.READY)
    def run(self):
        """Run an already configured scan"""
        if self.configured_steps.value < self.total_steps.value:
            next_state = sm.READY
        else:
            next_state = sm.IDLE
        self.try_stateful_function(sm.RUNNING, next_state, self._call_do_run)

    def _call_do_run(self):
        hook = self.Run
        while True:
            try:
                self.do_run(hook)
            except AbortedError:
                # Work out if it was an abort or pause
                state = self.state.value
                self.log_debug("Do run got AbortedError from %s", state)
                if state in (sm.SEEKING, sm.PAUSED):
                    # Wait to be restarted
                    task = Task("StateWaiter", self.process)
                    bad_states = [sm.DISABLING, sm.ABORTING, sm.FAULT]
                    try:
                        task.when_matches(self.state, sm.RUNNING, bad_states)
                    except BadValueError:
                        # raise AbortedError so we don't try to transition
                        raise AbortedError()
                    # Restart it
                    hook = self.Resume
                    self.status.set_value("Run resumed")
                else:
                    # just drop out
                    raise
            else:
                return

    def do_run(self, hook):
        self.run_hook(hook, self.part_tasks, self.update_completed_steps)
        self.transition(sm.POSTRUN, "Finishing run")
        completed_steps = self.configured_steps.value
        if completed_steps < self.total_steps.value:
            steps_to_do = self.steps_per_run
            part_info = self.run_hook(self.ReportStatus, self.part_tasks)
            self.completed_steps.set_value(completed_steps)
            self.run_hook(
                self.PostRunReady, self.part_tasks, completed_steps,
                steps_to_do, part_info, **self.configure_params)
            self.configured_steps.set_value(completed_steps + steps_to_do)
        else:
            self.run_hook(self.PostRunIdle, self.part_tasks)

    def update_completed_steps(self, completed_steps, part):
        # This is run in the child thread, so make sure it is thread safe
        self.progress_reporting[part] = completed_steps
        min_completed_steps = min(self.progress_reporting.values())
        if min_completed_steps > self.completed_steps.value:
            self.completed_steps.set_value(min_completed_steps)

    @method_writeable_in(
        sm.IDLE, sm.CONFIGURING, sm.READY, sm.RUNNING, sm.POSTRUN, sm.PAUSED,
        sm.SEEKING)
    def abort(self):
        self.try_stateful_function(
            sm.ABORTING, sm.ABORTED, self.do_abort, self.Abort)

    def do_abort(self, hook):
        for task in self.part_tasks.values():
            task.stop()
        self.run_hook(hook, self.create_part_tasks())
        for task in self.part_tasks.values():
            task.wait()

    def set_completed_steps(self, completed_steps):
        params = self.pause.MethodMeta.prepare_input_map(
            completedSteps=completed_steps)
        self.pause(params)

    @method_writeable_in(sm.READY, sm.PAUSED, sm.RUNNING)
    @method_takes("completedSteps", NumberMeta(
        "int32", "Step to mark as the last completed step, -1 for current"), -1)
    def pause(self, params):
        current_state = self.state.value
        if params.completedSteps < 0:
            completed_steps = self.completed_steps.value
        else:
            completed_steps = params.completedSteps
        if current_state == sm.RUNNING:
            next_state = sm.PAUSED
        else:
            next_state = current_state
        assert completed_steps < self.total_steps.value, \
            "Cannot seek to after the end of the scan"
        self.try_stateful_function(
            sm.SEEKING, next_state, self.do_pause, completed_steps)

    def do_pause(self, completed_steps):
        self.do_abort(self.Pause)
        in_run_steps = completed_steps % self.steps_per_run
        steps_to_do = self.steps_per_run - in_run_steps
        part_info = self.run_hook(self.ReportStatus, self.part_tasks)
        self.completed_steps.set_value(completed_steps)
        self.run_hook(
            self.Seek, self.part_tasks, completed_steps,
            steps_to_do, part_info, **self.configure_params)
        self.configured_steps.set_value(completed_steps + steps_to_do)

    @method_writeable_in(sm.PAUSED)
    def resume(self):
        self.transition(sm.RUNNING, "Resuming run")
        # self._call_do_run will now take over
