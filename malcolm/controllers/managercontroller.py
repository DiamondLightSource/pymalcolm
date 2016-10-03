from collections import OrderedDict

from malcolm.controllers.defaultcontroller import DefaultController
from malcolm.core import RunnableDeviceStateMachine, REQUIRED, method_returns, \
    method_only_in, method_takes, ElementMap, Attribute, Task, Hook, Table
from malcolm.core.vmetas import PointGeneratorMeta, StringArrayMeta, \
    NumberMeta, NumberArrayMeta, BooleanArrayMeta, TableMeta


sm = RunnableDeviceStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axes_to_move", StringArrayMeta("Axes that should be moved"), REQUIRED,
    "exposure", NumberMeta("float64", "How long to remain at each point"),
    REQUIRED]


# Make a table for the layout info we need
columns = OrderedDict()
columns["name"] = StringArrayMeta("Name of layout part")
columns["mri"] = StringArrayMeta("Malcolm full name of child block")
columns["x"] = NumberArrayMeta("float64", "X Co-ordinate of child block")
columns["y"] = NumberArrayMeta("float64", "X Co-ordinate of child block")
columns["visible"] = BooleanArrayMeta("Whether child block is visible")
layout_table_meta = TableMeta("Layout of child blocks", columns=columns)

# Make a table for the port info we need
columns = OrderedDict()
columns["name"] = StringArrayMeta("Name of layout part")
columns["type"] = StringArrayMeta("Type of outport (e.g. bit or pos)")
columns["value"] = StringArrayMeta("Value of outport (e.g. PULSE1.OUT)")
outport_table_meta = TableMeta("List of ports on blocks", columns=columns)


@sm.insert
@method_takes()
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # hooks
    Report = Hook()
    Validate = Hook()
    Configuring = Hook()
    PreRun = Hook()
    Running = Hook()
    PostRun = Hook()
    Aborting = Hook()
    UpdateLayout = Hook()
    ListOutports = Hook()

    # default attributes
    totalSteps = None
    layout = None

    # Params passed to configure()
    configure_params = None

    def create_attributes(self):
        self.totalSteps = NumberMeta(
            "int32", "Readback of number of scan steps"
        ).make_attribute(0)
        yield "totalSteps", self.totalSteps, None
        self.layout = layout_table_meta.make_attribute()
        yield "layout", self.layout, self.set_layout

    def do_reset(self):
        super(ManagerController, self).do_reset()
        self.set_layout(Table(layout_table_meta))

    def set_layout(self, value):
        outport_table = self.run_hook(
            self.ListOutports, self.create_part_tasks())
        layout_table = self.run_hook(
            self.UpdateLayout, self.create_part_tasks(), layout_table=value,
            outport_table=outport_table
        )
        self.layout.set_value(layout_table)

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
            # Transition first so no-one else can run configure()
            self.transition(sm.CONFIGURING, "Configuring", create_tasks=True)

            # Store the params and set attributes
            self.configure_params = params
            self.totalSteps.set_value(params.generator.num)
            self.block["completedSteps"].set_value(0)

            # Do the actual configure
            self.do_configure()
            self.transition(sm.READY, "Done configuring")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Configuring")
            self.transition(sm.FAULT, str(e))
            raise

    def do_configure(self, start_step=0):
        # Ask all parts to report relevant info and pass results to anyone
        # who cares
        info_table = self.run_hook(self.Report, self.part_tasks)
        # Pass results to anyone who cares
        self.run_hook(self.Configuring, self.part_tasks, info_table=info_table,
                      start_step=start_step, **self.configure_params)

    @method_only_in(sm.READY)
    def run(self):
        try:
            self.transition(sm.PRERUN, "Preparing for run")
            self._call_do_run()
            if self.block["completedSteps"].value < self.totalSteps.value:
                next_state = sm.READY
            else:
                next_state = sm.IDLE
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
            if state in (sm.REWINDING, sm.PAUSED):
                # Wait to be restarted
                self.log_debug("Waiting for PreRun")
                task = Task("StateWaiter", self.process)
                futures = task.when_matches(self.state, sm.PRERUN, [
                    sm.DISABLING, sm.ABORTING, sm.FAULT])
                task.wait_all(futures)
                # Restart it
                self.do_run()
            else:
                # just drop out
                self.log_debug("We were aborted")
                raise

    def do_run(self):
        self.run_hook(self.PreRun, self.part_tasks)
        self.transition(sm.RUNNING, "Waiting for scan to complete")
        self.run_hook(self.Running, self.part_tasks)
        self.transition(sm.POSTRUN, "Finishing run")
        self.run_hook(self.PostRun, self.part_tasks)

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
            self.do_configure(current_index)
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
            self.do_configure(requested_index)
            self.transition(sm.PAUSED, "Rewind finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Rewinding")
            self.transition(sm.FAULT, str(e))
            raise

    @method_only_in(sm.PAUSED)
    def resume(self):
        self.transition(sm.PRERUN, "Resuming run")





