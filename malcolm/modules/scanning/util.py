from annotypes import Anno, Array, Union, Sequence
from scanpointgenerator import CompoundGenerator

from malcolm.core import Serializable
from malcolm.modules.builtin.util import ManagerStates

with Anno("Generator instance providing specification for scan"):
    AGenerator = CompoundGenerator
with Anno("List of axes in inner dimension of generator that should be moved"):
    AAxesToMove = Array[str]
UAxesToMove = Union[AAxesToMove, Sequence[str]]


class ConfigureParams(Serializable):
    # This will be serialized, so maintain camelCase for axesToMove
    # noinspection PyPep8Naming
    def __init__(self, generator, axesToMove):
        # type: (AGenerator, UAxesToMove) -> None
        self.generator = generator
        self.axesToMove = AAxesToMove(axesToMove)


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