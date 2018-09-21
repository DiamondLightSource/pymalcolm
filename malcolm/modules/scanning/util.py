from annotypes import Anno, Array, Union, Sequence, Any
from scanpointgenerator import CompoundGenerator
import numpy as np

from malcolm.core import Serializable, VMeta, NTUnion, Widget
from malcolm.modules.builtin.util import ManagerStates

with Anno("Generator instance providing specification for scan"):
    AGenerator = CompoundGenerator
with Anno("List of axes in inner dimension of generator that should be moved"):
    AAxesToMove = Array[str]
UAxesToMove = Union[AAxesToMove, Sequence[str]]


class ConfigureParams(Serializable):
    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    def __init__(self, generator, axesToMove=None, **kwargs):
        # type: (AGenerator, UAxesToMove, **Any) -> None
        if kwargs:
            # Got some additional args to report
            self.call_types = self.call_types.copy()
            for k in kwargs:
                # We don't use this apart from its presence,
                # so no need to fill in description, typ, etc.
                self.call_types[k] = Anno("")
            self.__dict__.update(kwargs)
        self.generator = generator
        if axesToMove is None:
            axesToMove = generator.axes
        self.axesToMove = AAxesToMove(axesToMove)


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
        self.set_allowed(self.ARMED,
                         self.RUNNING, self.SEEKING, self.RESETTING)
        self.set_allowed(self.RUNNING, self.POSTRUN, self.SEEKING)
        self.set_allowed(self.POSTRUN, self.READY, self.ARMED)
        self.set_allowed(self.SEEKING, self.ARMED, self.PAUSED)
        self.set_allowed(self.PAUSED, self.SEEKING, self.RUNNING)

        # Add Abort to all normal states
        normal_states = [
            self.READY, self.CONFIGURING, self.ARMED, self.RUNNING,
            self.POSTRUN, self.PAUSED, self.SEEKING]
        for state in normal_states:
            self.set_allowed(state, self.ABORTING)

        # Set transitions for aborted states
        self.set_allowed(self.ABORTING, self.ABORTED)
        self.set_allowed(self.ABORTED, self.RESETTING)


@Serializable.register_subclass("malcolm:core/PointGeneratorMeta:1.0")
@VMeta.register_annotype_converter(CompoundGenerator)
class PointGeneratorMeta(VMeta):

    attribute_class = NTUnion

    def doc_type_string(self):
        return "CompoundGenerator"

    def default_widget(self):
        return Widget.TREE

    def validate(self, value):
        if value is None:
            return CompoundGenerator([], [], [])
        elif isinstance(value, CompoundGenerator):
            return value
        elif isinstance(value, dict):
            # Sanitise the dict in place
            # TODO: remove this when scanpoint generator supports ndarray inputs
            def sanitize(d):
                for k, v in d.items():
                    if isinstance(v, np.ndarray):
                        d[k] = list(v)
                    elif isinstance(v, list):
                        for x in v:
                            if isinstance(x, dict):
                                sanitize(x)
                    elif isinstance(v, dict):
                        sanitize(v)
            sanitize(value)
            return CompoundGenerator.from_dict(value)
        else:
            raise TypeError(
                "Value %s must be a Generator object or dictionary" % value)
