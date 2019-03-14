from annotypes import add_call_types, Anno

from malcolm.core import DEFAULT_TIMEOUT, PartRegistrar
from malcolm.modules import builtin
from malcolm.modules.builtin.parts import ChildPart
from ..util import CS_AXIS_NAMES


with Anno("Co-ordinate system number"):
    ACS = int
with Anno("Motor position to move to in EGUs"):
    ADemandPosition = float
with Anno("Time to take to perform move"):
    AMoveTime = float


class CSPart(ChildPart):
    # The context we will use for all our functions
    context = None

    def __init__(self, mri, cs):
        # type: (builtin.parts.AMri, ACS) -> None
        super(CSPart, self).__init__("CS%d" % cs, mri, initial_visibility=True)
        self.cs = cs

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(CSPart, self).setup(registrar)
        # Add methods
        registrar.add_method_model(self.move, "moveCS%d" % self.cs)

    @add_call_types
    def init(self, context):
        # type: (builtin.hooks.AContext) -> None
        # Store the context for later use
        self.context = context
        super(CSPart, self).init(context)
        # Check the port name matches our CS number
        child = context.block_view(self.mri)
        cs_port = child.port.value
        assert cs_port.endswith(str(self.cs)), \
            "CS Port %s doesn't end with port number %d" % (cs_port, self.cs)

    @add_call_types
    def move(self,
             a=None,  # type: ADemandPosition
             b=None,  # type: ADemandPosition
             c=None,  # type: ADemandPosition
             u=None,  # type: ADemandPosition
             v=None,  # type: ADemandPosition
             w=None,  # type: ADemandPosition
             x=None,  # type: ADemandPosition
             y=None,  # type: ADemandPosition
             z=None,  # type: ADemandPosition
             move_time=0  # type: AMoveTime
             ):
        # type: (...) -> None
        """Move the given CS axes using a deferred co-ordinated move"""
        child = self.context.block_view(self.mri)
        child.deferMoves.put_value(True)
        child.csMoveTime.put_value(move_time)
        # Add in the motors we need to move
        attribute_values = {}
        for axis in CS_AXIS_NAMES:
            demand = locals()[axis.lower()]
            if demand is not None:
                attribute_values["demand%s" % axis] = demand
        fs = child.put_attribute_values_async(attribute_values)
        # Wait for the demand to have been received by the PV
        for attr, value in sorted(attribute_values.items()):
            child.when_value_matches(attr, value, timeout=1.0)
        # Start the move
        child.deferMoves.put_value(False)
        # Wait for them to get there
        self.context.wait_all_futures(fs, timeout=move_time + DEFAULT_TIMEOUT)

#    def inverse_kinematics():
#    def forward_kinematics():
