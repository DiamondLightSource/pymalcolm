from malcolm.core import method_takes, REQUIRED, method_also_takes, \
    method_writeable_in, Hook, AbortedError, MethodModel, Queue, \
    call_with_params, Context, ABORT_TIMEOUT, TimeoutError, method_returns
from malcolm.modules.builtin.controllers import ManagerStates, \
    ManagerController
from malcolm.modules.builtin.vmetas import NumberMeta, StringArrayMeta
from malcolm.modules.scanning.infos import ParameterTweakInfo
from malcolm.modules.scanpointgenerator.vmetas import PointGeneratorMeta
from malcolm.tags import widget, config


class RunnableStates(ManagerStates):
    """A state set listing the valid transitions for a `RunnableController`"""

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
        self.set_allowed(self.ARMED, [
            self.RUNNING, self.SEEKING, self.RESETTING])
        self.set_allowed(self.RUNNING, [self.POSTRUN, self.SEEKING])
        self.set_allowed(self.POSTRUN, [self.READY, self.ARMED])
        self.set_allowed(self.SEEKING, [self.ARMED, self.PAUSED])
        self.set_allowed(self.PAUSED, [self.SEEKING, self.RUNNING])

        # Add Abort to all normal states
        normal_states = [
            self.READY, self.CONFIGURING, self.ARMED, self.RUNNING,
            self.POSTRUN, self.PAUSED, self.SEEKING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for aborted states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)


ss = RunnableStates


configure_args = (
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axesToMove", StringArrayMeta(
        "List of axes in inner dimension of generator that should be moved"),
    []
)
validate_args = configure_args[:-1] + (REQUIRED,)


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
    """Called before Validate, Configure, PostRunArmed and Seek hooks to report
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

    PostRunArmed = Hook()
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

    PostRunReady = Hook()
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

    # Configure method_models
    # {part: configure_method_model}
    configure_method_models = None

    # Stored for pause
    steps_per_run = 0

    # Progress reporting dict
    # {part: completed_steps for that part}
    progress_updates = None

    # Queue so that do_run can wait to see why it was aborted and resume if
    # needed
    resume_queue = None

    # Queue so we can wait for aborts to complete
    abort_queue = None

    @method_writeable_in(ss.FAULT, ss.DISABLED, ss.ABORTED, ss.ARMED)
    def reset(self):
        # Override reset to work from aborted too
        super(RunnableController, self).reset()

    def create_attribute_models(self):
        for data in super(RunnableController, self).create_attribute_models():
            yield data
        # Create sometimes writeable attribute for the current completed scan
        # step
        completed_steps_meta = NumberMeta(
            "int32", "Readback of number of scan steps",
            tags=[widget("textinput")])
        completed_steps_meta.set_writeable_in(ss.PAUSED, ss.ARMED)
        self.completed_steps = completed_steps_meta.create_attribute_model(0)
        yield "completedSteps", self.completed_steps, self.set_completed_steps
        # Create read-only attribute for the number of configured scan steps
        configured_steps_meta = NumberMeta(
            "int32", "Number of steps currently configured",
            tags=[widget("textupdate")])
        self.configured_steps = configured_steps_meta.create_attribute_model(0)
        yield "configuredSteps", self.configured_steps, None
        # Create read-only attribute for the total number scan steps
        total_steps_meta = NumberMeta(
            "int32", "Readback of number of scan steps",
            tags=[widget("textupdate")])
        self.total_steps = total_steps_meta.create_attribute_model(0)
        yield "totalSteps", self.total_steps, None
        # Create sometimes writeable attribute for the default axis names
        axes_to_move_meta = StringArrayMeta(
            "Default axis names to scan for configure()",
            tags=[widget("table"), config()])
        axes_to_move_meta.set_writeable_in(ss.READY)
        self.axes_to_move = axes_to_move_meta.create_attribute_model(
            self.params.axesToMove)
        yield "axesToMove", self.axes_to_move, self.set_axes_to_move

    def do_init(self):
        self.part_contexts = {}
        # Populate configure args from any child method hooked to Configure.
        # If we have runnablechildparts, they will call update_configure_args
        # during do_init
        self.configure_method_models = {}
        # Look for all parts that hook into Configure
        for part, func_name in self._hooked_func_names[self.Configure].items():
            if func_name in part.method_models:
                self.update_configure_args(part, part.method_models[func_name])
        super(RunnableController, self).do_init()

    def do_reset(self):
        super(RunnableController, self).do_reset()
        self.configured_steps.set_value(0)
        self.completed_steps.set_value(0)
        self.total_steps.set_value(0)

    def update_configure_args(self, part, configure_model):
        """Tell controller part needs different things passed to Configure"""
        with self.changes_squashed:
            # Update the dict
            self.configure_method_models[part] = configure_model
            method_models = list(self.configure_method_models.values())

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

    @method_takes(*configure_args)
    @method_returns(*validate_args)
    def validate(self, params, returns):
        """Validate configuration parameters and return validated parameters.

        Doesn't take device state into account so can be run in any state
        """
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

    def abortable_transition(self, state):
        with self._lock:
            # We might have been aborted just now, so this will fail
            # with an AbortedError if we were
            self.part_contexts[self].sleep(0)
            self.transition(state)

    @method_takes(*configure_args)
    @method_writeable_in(ss.READY)
    def configure(self, params):
        """Validate the params then configure the device ready for run().

        Try to prepare the device as much as possible so that run() is quick to
        start, this may involve potentially long running activities like moving
        motors.

        Normally it will return in Armed state. If the user aborts then it will
        return in Aborted state. If something goes wrong it will return in Fault
        state. If the user disables then it will return in Disabled state.
        """
        self.validate(params, params)
        try:
            self.transition(ss.CONFIGURING)
            self.do_configure(params)
            self.abortable_transition(ss.ARMED)
        except AbortedError:
            self.abort_queue.put(None)
            raise
        except Exception as e:
            self.go_to_error_state(e)
            raise

    def do_configure(self, params):
        # These are the part tasks that abort() and pause() will operate on
        self.part_contexts = self.create_part_contexts()
        # Tell these contexts to notify their parts that about things they
        # modify so it doesn't screw up the modified led
        for part, context in self.part_contexts.items():
            context.set_notify_dispatch_request(part.notify_dispatch_request)
        # So add one for ourself too so we can be aborted
        self.part_contexts[self] = Context(self.process)
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
        """Run a device where configure() has already be called

        Normally it will return in Ready state. If setup for multiple-runs with
        a single configure() then it will return in Armed state. If the user
        aborts then it will return in Aborted state. If something goes wrong it
        will return in Fault state. If the user disables then it will return in
        Disabled state.
        """
        if self.configured_steps.value < self.total_steps.value:
            next_state = ss.ARMED
        else:
            next_state = ss.READY
        try:
            self.transition(ss.RUNNING)
            hook = self.Run
            going = True
            while going:
                try:
                    self.do_run(hook)
                except AbortedError:
                    self.abort_queue.put(None)
                    # Wait for a response on the resume_queue
                    should_resume = self.resume_queue.get()
                    if should_resume:
                        # we need to resume
                        hook = self.Resume
                        self.log.debug("Resuming run")
                    else:
                        # we don't need to resume, just drop out
                        raise
                else:
                    going = False
            self.abortable_transition(next_state)
        except AbortedError:
            raise
        except Exception as e:
            self.go_to_error_state(e)
            raise

    def do_run(self, hook):
        self.run_hook(hook, self.part_contexts, self.update_completed_steps)
        self.abortable_transition(ss.POSTRUN)
        completed_steps = self.configured_steps.value
        if completed_steps < self.total_steps.value:
            steps_to_do = self.steps_per_run
            part_info = self.run_hook(self.ReportStatus, self.part_contexts)
            self.completed_steps.set_value(completed_steps)
            self.run_hook(
                self.PostRunArmed, self.part_contexts, completed_steps,
                steps_to_do, part_info, **self.configure_params)
            self.configured_steps.set_value(completed_steps + steps_to_do)
        else:
            self.run_hook(self.PostRunReady, self.part_contexts)

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
        """Abort the current operation and block until aborted

        Normally it will return in Aborted state. If something goes wrong it
        will return in Fault state. If the user disables then it will return in
        Disabled state.
        """
        # Tell _call_do_run not to resume
        if self.resume_queue:
            self.resume_queue.put(False)
        self.try_aborting_function(ss.ABORTING, ss.ABORTED, self.do_abort)

    def do_abort(self):
        self.run_hook(self.Abort, self.create_part_contexts())

    def try_aborting_function(self, start_state, end_state, func, *args):
        try:
            # To make the running function fail we need to stop any running
            # contexts (if running a hook) or make transition() fail with
            # AbortedError. Both of these are accomplished here
            with self._lock:
                original_state = self.state.value
                self.abort_queue = Queue()
                self.transition(start_state)
                for context in self.part_contexts.values():
                    context.stop()
            if original_state not in (ss.READY, ss.ARMED, ss.PAUSED):
                # Something was running, let it finish aborting
                try:
                    self.abort_queue.get(timeout=ABORT_TIMEOUT)
                except TimeoutError:
                    self.log.warning("Timeout waiting while %s" % start_state)
            with self._lock:
                # Now we've waited for a while we can remove the error state
                # for transition in case a hook triggered it rather than a
                # transition
                self.part_contexts[self].ignore_stops_before_now()
            func(*args)
            self.abortable_transition(end_state)
        except AbortedError:
            self.abort_queue.put(None)
            raise
        except Exception as e:  # pylint:disable=broad-except
            self.go_to_error_state(e)
            raise

    def set_completed_steps(self, completed_steps):
        """Seek a Armed or Paused scan back to another value

        Normally it will return in the state it started in. If the user aborts
        then it will return in Aborted state. If something goes wrong it will
        return in Fault state. If the user disables then it will return in
        Disabled state.
        """
        call_with_params(self.pause, completedSteps=completed_steps)

    @method_writeable_in(ss.ARMED, ss.PAUSED, ss.RUNNING)
    @method_takes("completedSteps", NumberMeta(
        "int32", "Step to mark as the last completed step, -1 for current"), -1)
    def pause(self, params):
        """Pause a run() so that resume() can be called later.

        The original call to run() will not be interrupted by pause(), it will
        with until the scan completes or is aborted.

        Normally it will return in Paused state. If the user aborts then it will
        return in Aborted state. If something goes wrong it will return in Fault
        state. If the user disables then it will return in Disabled state.
        """
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
        self.try_aborting_function(
            ss.SEEKING, next_state, self.do_pause, completed_steps)

    def do_pause(self, completed_steps):
        self.run_hook(self.Pause, self.create_part_contexts())
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
        """Resume a paused scan.

        Normally it will return in Running state. If something goes wrong it
        will return in Fault state.
        """
        self.transition(ss.RUNNING)
        self.resume_queue.put(True)
        # self.run will now take over

    def do_disable(self):
        # Abort anything that is currently running, but don't wait
        for context in self.part_contexts.values():
            context.stop()
        if self.resume_queue:
            self.resume_queue.put(False)
        super(RunnableController, self).do_disable()
