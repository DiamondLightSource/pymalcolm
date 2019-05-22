from annotypes import Anno

from malcolm.core import Part, PartRegistrar, NumberMeta, APartName, \
    AMetaDescription, Display, APrecision, AUnits, ALimitHigh, ALimitLow
from ..util import set_tags, AWriteable, AConfig, AGroup, AWidget

with Anno("Initial value of the created attribute"):
    AValue = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMetaDescription = AMetaDescription
APrecision = APrecision
AUnits = AUnits
ALimitHigh = ALimitHigh
ALimitLow = ALimitLow
AWriteable = AWriteable
AConfig = AConfig
AGroup = AGroup
AWidget = AWidget


class Float64Part(Part):
    """Create a single float64 Attribute on the Block"""
    def __init__(self,
                 name,  # type: APartName
                 description,  # type: AMetaDescription
                 writeable=False,  # type: AWriteable
                 config=1,  # type: AConfig
                 group=None,  # type: AGroup
                 widget=None,  # type: AWidget
                 value=0.0,  # type: AValue
                 limit_low=0,  # type: ALimitLow
                 limit_high=0,  # type: ALimitHigh
                 precision=8,  # type: APrecision
                 units="",  # type: AUnits
                 ):
        # type: (...) -> None
        super(Float64Part, self).__init__(name)
        display = Display(limitLow=limit_low,
                          limitHigh=limit_high,
                          precision=precision,
                          units=units)
        meta = NumberMeta("float64", description, display=display)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
