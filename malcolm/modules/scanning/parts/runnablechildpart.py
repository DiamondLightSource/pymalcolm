from annotypes import add_call_types, Anno, Union, Array, Sequence

from malcolm.core import BadValueError, serialize_object, Part, APartName, \
    Delta, deserialize_object, Subscribe, MethodModel, Unsubscribe, \
    Future, PartRegistrar
from malcolm.modules.builtin.parts import ChildPart, AMri
from malcolm.modules.builtin.hooks import InitHook, HaltHook, ResetHook
from malcolm.modules.scanning.hooks import ConfigureHook, PostRunArmedHook, \
    SeekHook, RunHook, ResumeHook, ACompletedSteps, AContext, ValidateHook, \
    AConfigureParams, UParameterTweakInfos, PostRunReadyHook, AbortHook
from malcolm.modules.scanning.infos import ParameterTweakInfo, \
    ConfigureParamsInfo, RunProgressInfo
from malcolm.modules.scanning.util import ConfigureParams, UAxesToMove, \
    AGenerator, RunnableStates

with Anno("The configure arguments we shouldn't publish to our parent"):
    AIgnoreConfigureArgs = Array[str]
UIgnoreConfigureArgs = Union[AIgnoreConfigureArgs, Sequence[str], str]

ss = RunnableStates


class RunnableChildPart(Part):
    """Part controlling a child Block that exposes a configure/run interface"""

    def __init__(self, name, mri, ignore_configure_args=()):
        # type: (APartName, AMri, UIgnoreConfigureArgs) -> None
        super(RunnableChildPart, self).__init__(name)
        self.mri = mri
        self.ignore_configure_args = AIgnoreConfigureArgs(ignore_configure_args)
        self.cp = ChildPart(name, mri)
        # Stored between runs
        self.run_future = None  # type: Future
        # The serialized configure method
        self.serialized_configure = MethodModel().to_dict()
        # The registrar object we get at setup
        self.registrar = None  # type: PartRegistrar

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        self.registrar = registrar
        self.cp.setup(registrar)

    def update_part_configure_args(self, response):
        # Decorate validate and configure with the sum of its parts
        if isinstance(response, Delta):
            # Check if the changes contain more than just writeable change
            writeable_path = [c[0] and c[0][-1] == "writeable"
                              for c in response.changes]
            if all(writeable_path):
                return
        else:
            # Return or Error is the end of our subscription, log and ignore
            self.log.debug(
                "update_part_configure_args got response %r", response)
            return

        response.apply_changes_to(self.serialized_configure)
        configure_model = deserialize_object(
            self.serialized_configure, MethodModel)  # type: MethodModel

        # Create a new ConfigureParams subclass from the union of all the
        # call_types
        class ConfigureParamsSubclass(ConfigureParams):
            # This will be serialized, so maintain camelCase for axesToMove
            # noinspection PyPep8Naming
            def __init__(self, generator, axesToMove, **kwargs):
                # type: (AGenerator, UAxesToMove) -> None
                super(ConfigureParamsSubclass, self).__init__(
                    generator, axesToMove)
                self.__dict__.update(kwargs)

        # Store it and update its call_types
        for k, meta in configure_model.takes.elements.items():
            if k not in self.ignore_configure_args:
                anno = meta.to_anno()
                if k in configure_model.defaults:
                    anno.default = configure_model.defaults[k]
                elif k not in configure_model.takes.required:
                    anno.default = None
                ConfigureParamsSubclass.call_types[k] = anno

        # Notify the controller
        self.registrar.report(ConfigureParamsInfo(ConfigureParamsSubclass))

    def on_hook(self, hook):
        if isinstance(hook, InitHook):
            hook.run(self.init)
        elif isinstance(hook, HaltHook):
            hook.run(self.halt)
        elif isinstance(hook, ResetHook):
            hook.run(self.reset)
        elif isinstance(hook, ValidateHook):
            hook.run(self.validate)
        elif isinstance(hook, ConfigureHook):
            hook.run(self.configure)
        elif isinstance(hook, (RunHook, ResumeHook)):
            hook.run(self.run)
        elif isinstance(hook, (PostRunArmedHook, PostRunReadyHook)):
            hook.run(self.post_run)
        elif isinstance(hook, SeekHook):
            hook.run(self.seek)
        elif isinstance(hook, AbortHook):
            hook.run(self.abort)
        else:
            self.cp.on_hook(hook)

    @add_call_types
    def init(self, context):
        # type: (AContext) -> None
        self.cp.init(context)
        # Monitor the child configure Method for changes
        subscription = Subscribe(path=[self.mri, "configure"], delta=True)
        subscription.set_callback(self.update_part_configure_args)
        # Wait for the first update to come in
        self.cp.child_controller.handle_request(subscription).wait()

    @add_call_types
    def halt(self):
        # type: () -> None
        self.cp.halt()
        unsubscribe = Unsubscribe()
        unsubscribe.set_callback(self.update_part_configure_args)
        self.child_controller.handle_request(unsubscribe)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        if child.abort.writeable:
            child.abort()
        if child.reset.writeable:
            child.reset()

    # We might get different params class because of update_part_configure_args
    @add_call_types
    def validate(self, context, params):
        # type: (AContext, AConfigureParams) -> UParameterTweakInfos
        child = context.block_view(self.mri)
        returns = child.validate(**params.to_dict())
        ret = []
        for k, v in returns.items():
            if serialize_object(params[k]) != serialize_object(v):
                ret.append(ParameterTweakInfo(k, v))
        return ret

    # We might get different params class because of update_part_configure_args
    @add_call_types
    def configure(self, context, params):
        # type: (AContext, AConfigureParams) -> None
        child = context.block_view(self.mri)
        # If we have done a save or load with the child having a particular
        # design then make sure the child now has that design
        design = self.cp.saved_structure.get("design", "")
        if design:
            child.design.put_value(design)
        child.configure(**params.to_dict())

    def update_completed_steps(self, value):
        # type: (int) -> None
        self.registrar.report(RunProgressInfo(value))

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.completedSteps.subscribe_value(self.update_completed_steps)
        bad_states = [ss.DISABLING, ss.ABORTING, ss.FAULT]
        match_future = child.when_value_matches_async(
            "state", ss.POSTRUN, bad_states)
        if child.state.value == ss.ARMED:
            self.run_future = child.run_async()
        else:
            child.resume()
        try:
            context.wait_all_futures(match_future)
        except BadValueError:
            # If child went into Fault state, raise the friendlier run_future
            # exception
            if child.state.value == ss.FAULT:
                raise self.run_future.exception()
            else:
                raise

    @add_call_types
    def post_run(self, context):
        # type: (AContext) -> None
        context.wait_all_futures(self.run_future)

    @add_call_types
    def seek(self, context, completed_steps):
        # type: (AContext, ACompletedSteps) -> None
        # Clear out the update_completed_steps and match_future subscriptions
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.pause(completedSteps=completed_steps)

    @add_call_types
    def abort(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        child.abort()
