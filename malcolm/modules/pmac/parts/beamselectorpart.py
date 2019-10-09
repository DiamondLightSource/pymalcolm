from annotypes import Anno, add_call_types, TYPE_CHECKING

from malcolm.core import PartRegistrar, NumberMeta, config_tag, Widget
from malcolm.modules import builtin

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri
AIV = builtin.parts.AInitialVisibility

with Anno("The demand value to move our counter motor to"):
    ADemand = float

# TODO Type checking?

class BeamSelectorPart(builtin.parts.ChildPart):

    def __init__(self,
                 name, # type: APartName
                 mri, # type: AMri,
                 initial_visibility = False # type: AIV
                 ):
        # type: (...) -> None

        super(BeamSelectorPart, self).__init__(name,
                                               mri,
                                               stateful=False,
                                               initial_visibility=True)

    def setup(self, registrar):
        # type: (PartRegistrar) -> None

        super(BeamSelectorPart, self).setup(registrar)

        self.angle = NumberMeta("float64",
                                "The current angle of beam selector",
                                tags=[config_tag(),
                                      Widget.TEXTINPUT.tag()]
                                ).create_attribute_model()
        registrar.add_attribute_model("angle",
                                      self.angle,
                                      self.angle.set_value)

        registrar.add_method_model(self.move,
                                   self.name,
                                   needs_context=True)

    @add_call_types
    def move(self, context, angle):
        # type: (builtin.hooks.AContext, ADemand) -> None

        #self.angle.set_value(angle)
        childBlock = context.block_view(self.mri)
        #child.put(self.mri, angle)
        childBlock.demand.put_value(angle)

        pass