from malcolm.core import method_takes, REQUIRED, method_also_takes, \
    method_writeable_in, Hook, AbortedError, MethodModel, Queue, \
    call_with_params
from malcolm.modules.builtin.controllers import ManagerStates, \
    ManagerController
from malcolm.modules.builtin.vmetas import NumberMeta, StringArrayMeta
from malcolm.modules.scanning.infos import ParameterTweakInfo
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from malcolm.tags import widget


class RunnableStates(ManagerStates):

    CONFIGURING = "Configuring"
    ARMED = "Armed"
    RUNNING = "Running"
    POSTRUN = "PostRun"
    PAUSED = "Paused"
    SEEKING = "Seeking"
    ABORTING = "Aborting"
    ABORTED = "Aborted"

    def create_block_transitions(self):
        super(RunnableStates, self).create_block_transitions()
        # Set transitions for normal states
        self.set_allowed(self.READY, self.CONFIGURING)
        self.set_allowed(self.CONFIGURING, self.ARMED)
        self.set_allowed(
            self.ARMED, [self.RUNNING, self.SEEKING, self.RESETTING])
        self.set_allowed(self.RUNNING, [self.POSTRUN, self.SEEKING])
        self.set_allowed(self.POSTRUN, [self.READY, self.ARMED])
        self.set_allowed(self.PAUSED, [self.SEEKING, self.RUNNING])
        self.set_allowed(self.SEEKING, [self.ARMED, self.PAUSED])

        # Add Abort to all normal states
        normal_states = [
            self.READY, self.CONFIGURING, self.ARMED, self.RUNNING,
            self.POSTRUN, self.PAUSED, self.SEEKING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for other states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)


ss = RunnableStates


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
    # The stateSet that this controller implements
    stateSet = ss()

    Validate = Hook()
    """Called at validate() to check parameters are valid

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
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
        context (Context): The context that should be used to perform operations
            on child blocks

    Returns:
        [`Info`] - any configuration Info objects relevant to other parts
    """

    Configure = Hook()
    """Called at configure() to configure child block for a run

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
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
        context (Context): The context that should be used to perform operations
            on child blocks
        part_info (dict): {part_name: [Info]} returned from Configure hook
    """

    Run = Hook()
    """Called at run() to start the configured steps running

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        update_completed_steps (callable): If part can report progress, this
            part should call update_completed_steps(completed_steps, self) with
            the integer step value each time progress is updated
    """

    PostRunReady = Hook()
    """Called at the end of run() when there are more steps to be run

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        completed_steps (int): Number of steps already completed
        steps_to_do (int): Number of steps we should configure for
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part configure()
            method_takes() decorator
    """

    PostRunIdle = Hook()
    """Called at the end of run() when there are no more steps to be run

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Pause = Hook()
    """Called at pause() to pause the current scan before Seek is called

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    Seek = Hook()
    """Called at seek() or at the end of pause() to reconfigure for a different
    number of completed_steps

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        completed_steps (int): Number of steps already completed
        steps_to_do (int): Number of steps we should configure for
        part_info (dict): {part_name: [Info]} returned from ReportStatus
        params (Map): Any configuration parameters asked for by part configure()
            method_takes() decorator
    """

    Resume = Hook()
    """Called at resume() to continue a paused scan

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
        update_completed_steps (callable): If part can report progress, this
            part should call update_completed_steps(completed_steps, self) with
            the integer step value each time progress is updated
    """

    Abort = Hook()
    """Called at abort() to stop the current scan

    Args:
        context (Context): The context that should be used to perform operations
            on child blocks
    """

    # Attributes
    completed_steps = None
    configured_steps = None
    total_steps = None
    axes_to_move = None

    # Params passed to configure()
    configure_params = None
    
    # Shared contexts between Configure, Run, Pause, Seek, Resume
    part_contexts = None

    # Stored for pause
    steps_per_run = 0

    # Progress reporting dict
    # {part: completed_steps for that part}
    progress_updates = None

    # Queue so that do_run can wait to see why it was aborted and resume if
    # needed
    resume_queue = None

    @method_writeable_in(ss.FAULT, ss.DISABLED, ss.ABORTED, ss.ARMED)
    def reset(self):
        # Override reset to work from aborted and ready too
        super(RunnableController, self).reset()

    def create_attributes(self):
        for data in super(RunnableController, self).create_attributes():
            yield data
        self.completed_steps = NumberMeta(
            "int32", "Readback of number of scan steps",
            tags=[widget("textupdate")]).create_attribute(0)
        self.completed_steps.meta.set_writeable_in(
            ss.PAUSED, ss.ARMED)
        yield "completedSteps", self.completed_steps, self.set_completed_steps
        self.configured_steps = NumberMeta(
            "int32", "Number of steps currently configured",
            tags=[widget("textupdate")]).create_attribute(0)
        yield "configuredSteps", self.configured_steps, None
        self.total_steps = NumberMeta(
            "int32", "Readback of number of scan steps",
            tags=[widget("textupdate")]).create_attribute(0)
        yield "totalSteps", self.total_steps, None
        self.axes_to_move = StringArrayMeta(
            "Default axis names to scan for configure()",
            tags=[widget("table")]
        ).create_attribute(self.params.axesToMove)
        self.axes_to_move.meta.set_writeable_in(ss.READY)
        yield "axesToMove", self.axes_to_move, self.set_axes_to_move

    def do_init(self):
        super(RunnableController, self).do_init()
        self.part_contexts = {}
        self.update_configure_args()

    def do_reset(self):
        super(RunnableController, self).do_reset()
        self.configured_steps.set_value(0)
        self.completed_steps.set_value(0)
        self.total_steps.set_value(0)

    def go_to_error_state(self, exception):
        if isinstance(exception, AbortedError):
            self.log.info("Got AbortedError in %s" % self.state.value)
        else:
            super(RunnableController, self).go_to_error_state(exception)

    def update_configure_args(self):
        with self.changes_squashed:
            # Look for all parts that hook into Configure
            configure_funcs = self._hooked_func_names[self.Configure]
            method_models = []
            for part, func_name in configure_funcs.items():
                method_models.append(part.method_models[func_name])

            # Update takes with the things we need
            default_configure = MethodModel.from_dict(
                RunnableController.configure.MethodModel.to_dict())
            default_configure.defaults["axesToMove"] = self.axes_to_move.value
            method_models.append(default_configure)

            # Decorate validate and configure with the sum of its parts
            self._block.validate.recreate_from_others(method_models)
            self._block.validate.set_returns(self._block.validate.takes)
            self._block.configure.recreate_from_others(method_models)

    def set_axes_to_move(self, value):
        self.axes_to_move.set_value(value)
        self.update_configure_args()

    @method_takes(*configure_args)
    def validate(self, params, returns):
        iterations = 10
        # Make some tasks just for validate
        part_contexts = self.create_part_contexts()
        # Get any status from all parts
        status_part_info = self.run_hook(self.ReportStatus, part_contexts)
        while iterations > 0:
            # Try up to 10 times to get a valid set of parameters
            iterations -= 1
            # Validate the params with all the parts
            validate_part_info = self.run_hook(
                self.Validate, part_contexts, status_part_info, **params)
            tweaks = ParameterTweakInfo.filter_values(validate_part_info)
            if tweaks:
                for tweak in tweaks:
                    params[tweak.parameter] = tweak.value
                    self.log.debug(
                        "Tweaking %s to %s", tweak.parameter, tweak.value)
            else:
                # Consistent set, just return the params
                return params
        raise ValueError("Could not get a consistent set of parameters")

    @method_takes(*configure_args)
    @method_writeable_in(ss.READY)
    def configure(self, params):
        """Configure for a scan"""
        self.validate(params, params)
        self.try_stateful_function(
            ss.CONFIGURING, ss.ARMED, self.do_configure,
            params)

    def do_configure(self, params):
        # These are the part tasks that abort() and pause() will operate on
        self.part_contexts = self.create_part_contexts()
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
        part_info = self.run_hook(self.ReportStatus, self.part_contexts)
        # Run the configure command on all parts, passing them info from
        # ReportStatus. Parts should return any reporting info for PostConfigure
        completed_steps = 0
        steps_to_do = self.steps_per_run
        part_info = self.run_hook(
            self.Configure, self.part_contexts, completed_steps, steps_to_do,
            part_info, **self.configure_params)
        # Take configuration info and reflect it as attribute updates
        self.run_hook(self.PostConfigure, self.part_contexts, part_info)
        # Update the completed and configured steps
        self.configured_steps.set_value(steps_to_do)
        # Reset the progress of all child parts
        self.progress_updates = {}
        self.resume_queue = Queue()

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

    @method_writeable_in(ss.ARMED)
    def run(self):
        """Run an already configured scan"""
        if self.configured_steps.value < self.total_steps.value:
            next_state = ss.ARMED
        else:
            next_state = ss.READY
        self.try_stateful_function(
                ss.RUNNING, next_state, self._call_do_run)

    def _call_do_run(self):
        hook = self.Run
        while True:
            try:
                return self.do_run(hook)
            except AbortedError:
                # Wait for a response on the resume_queue
                should_resume = self.resume_queue.get()
                if should_resume:
                    # we need to resume
                    hook = self.Resume
                    self.log.debug("Resuming run")
                else:
                    # we don't need to resume, just drop out
                    raise

    def do_run(self, hook):
        self.run_hook(hook, self.part_contexts, self.update_completed_steps)
        self.transition(ss.POSTRUN)
        completed_steps = self.configured_steps.value
        if completed_steps < self.total_steps.value:
            steps_to_do = self.steps_per_run
            part_info = self.run_hook(self.ReportStatus, self.part_contexts)
            self.completed_steps.set_value(completed_steps)
            self.run_hook(
                self.PostRunReady, self.part_contexts, completed_steps,
                steps_to_do, part_info, **self.configure_params)
            self.configured_steps.set_value(completed_steps + steps_to_do)
        else:
            self.run_hook(self.PostRunIdle, self.part_contexts)

    def update_completed_steps(self, completed_steps, part):
        with self._lock:
            # Update
            self.progress_updates[part] = completed_steps
            min_completed_steps = min(self.progress_updates.values())
            if min_completed_steps > self.completed_steps.value:
                self.completed_steps.set_value(min_completed_steps)

    @method_writeable_in(
        ss.READY, ss.CONFIGURING, ss.ARMED, ss.RUNNING, ss.POSTRUN, ss.PAUSED,
        ss.SEEKING)
    def abort(self):
        self.try_stateful_function(
            ss.ABORTING, ss.ABORTED, self.do_abort,
            self.Abort)

    def do_abort(self, hook):
        for context in self.part_contexts.values():
            context.stop()
        for context in self.part_contexts.values():
            if context.runner:
                context.runner.wait()
        self.run_hook(hook, self.create_part_contexts())
        # Tell _call_do_run not to resume if we are aborting
        if hook is self.Abort and self.resume_queue:
            self.resume_queue.put(False)

    def set_completed_steps(self, completed_steps):
        call_with_params(self.pause, completedSteps=completed_steps)

    @method_writeable_in(ss.ARMED, ss.PAUSED, ss.RUNNING)
    @method_takes("completedSteps", NumberMeta(
        "int32", "Step to mark as the last completed step, -1 for current"), -1)
    def pause(self, params):
        current_state = self.state.value
        if params.completedSteps < 0:
            completed_steps = self.completed_steps.value
        else:
            completed_steps = params.completedSteps
        if current_state == ss.RUNNING:
            next_state = ss.PAUSED
        else:
            next_state = current_state
        assert completed_steps < self.total_steps.value, \
            "Cannot seek to after the end of the scan"
        self.try_stateful_function(
            ss.SEEKING, next_state, self.do_pause, completed_steps)

    def do_pause(self, completed_steps):
        self.do_abort(self.Pause)
        in_run_steps = completed_steps % self.steps_per_run
        steps_to_do = self.steps_per_run - in_run_steps
        part_info = self.run_hook(self.ReportStatus, self.part_contexts)
        self.completed_steps.set_value(completed_steps)
        self.run_hook(
            self.Seek, self.part_contexts, completed_steps,
            steps_to_do, part_info, **self.configure_params)
        self.configured_steps.set_value(completed_steps + steps_to_do)

    @method_writeable_in(ss.PAUSED)
    def resume(self):
        self.transition(ss.RUNNING)
        self.resume_queue.put(True)
        # self._call_do_run will now take over

    def do_disable(self):
        # Abort anything that is currently running
        for context in self.part_contexts.values():
            context.stop()
        if self.resume_queue:
            self.resume_queue.put(False)
        super(RunnableController, self).do_disable()
