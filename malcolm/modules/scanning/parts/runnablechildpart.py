from annotypes import add_call_types, Anno, Union, Array, Sequence, Any

from malcolm.core import BadValueError, serialize_object, APartName, \
    Delta, deserialize_object, Subscribe, MethodModel, Unsubscribe, \
    Future, PartRegistrar
from malcolm.modules.builtin.parts import ChildPart, AMri, AInitialVisibility
from ..hooks import ConfigureHook, PostRunArmedHook, \
    SeekHook, RunHook, ResumeHook, ACompletedSteps, AContext, ValidateHook, \
    UParameterTweakInfos, PostRunReadyHook, AbortHook
from ..infos import ParameterTweakInfo, ConfigureParamsInfo, RunProgressInfo
from ..util import RunnableStates

with Anno("The configure arguments we shouldn't publish to our parent"):
    AIgnoreConfigureArgs = Array[str]
UIgnoreConfigureArgs = Union[AIgnoreConfigureArgs, Sequence[str], str]

ss = RunnableStates


class RunnableChildPart(ChildPart):
    """Part controlling a child Block that exposes a configure/run interface"""

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 initial_visibility=False,  # type: AInitialVisibility
                 ignore_configure_args=(),  # type: UIgnoreConfigureArgs
                 ):
        # type: (...) -> None
        super(RunnableChildPart, self).__init__(name, mri, initial_visibility)
        self.ignore_configure_args = AIgnoreConfigureArgs(ignore_configure_args)
        # Stored between runs
        self.run_future = None  # type: Future
        # The serialized configure method
        self.serialized_configure = MethodModel().to_dict()
        # The registrar object we get at setup
        self.registrar = None  # type: PartRegistrar

    @add_call_types
    def init(self, context):
        # type: (AContext) -> None
        super(RunnableChildPart, self).init(context)
        # Monitor the child configure Method for changes
        subscription = Subscribe(path=[self.mri, "configure"], delta=True)
        subscription.set_callback(self.update_part_configure_args)
        # Wait for the first update to come in
        self.child_controller.handle_request(subscription).wait()

    @add_call_types
    def halt(self):
        # type: () -> None
        super(RunnableChildPart, self).halt()
        unsubscribe = Unsubscribe()
        unsubscribe.set_callback(self.update_part_configure_args)
        self.child_controller.handle_request(unsubscribe)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        if child.abort.writeable:
            child.abort()
        super(RunnableChildPart, self).reset(context)

    def on_hook(self, hook):
        if isinstance(hook, ValidateHook):
            hook(self.validate, self.serialized_configure["takes"]["elements"])
        elif isinstance(hook, ConfigureHook):
            hook(self.configure, self.serialized_configure["takes"]["elements"])
        elif isinstance(hook, (RunHook, ResumeHook)):
            hook(self.run)
        elif isinstance(hook, (PostRunArmedHook, PostRunReadyHook)):
            hook(self.post_run)
        elif isinstance(hook, SeekHook):
            hook(self.seek)
        elif isinstance(hook, AbortHook):
            hook(self.abort)
        else:
            super(RunnableChildPart, self).on_hook(hook)

    @add_call_types
    def validate(self, context, **kwargs):
        # type: (AContext, **Any) -> UParameterTweakInfos
        child = context.block_view(self.mri)
        returns = child.validate(**kwargs)
        ret = []
        for k, v in serialize_object(returns).items():
            if serialize_object(kwargs[k]) != v:
                ret.append(ParameterTweakInfo(k, v))
        return ret

    @add_call_types
    def configure(self, context, **kwargs):
        # type: (AContext, **Any) -> None
        child = context.block_view(self.mri)
        # If we have done a save or load with the child having a particular
        # design then make sure the child now has that design
        design = self.saved_structure.get("design", "")
        if design:
            child.design.put_value(design)
        child.configure(**kwargs)

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

    def update_completed_steps(self, value):
        # type: (int) -> None
        self.registrar.report(RunProgressInfo(value))

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
        for k in self.ignore_configure_args:
            configure_model.takes.elements.pop(k, None)
            configure_model.defaults.pop(k, None)
        required = [x for x in configure_model.takes.required
                    if x not in self.ignore_configure_args]

        # Notify the controller that we have some new parameters to take
        self.registrar.report(ConfigureParamsInfo(
            metas=configure_model.takes.elements, required=required,
            defaults=configure_model.defaults))
