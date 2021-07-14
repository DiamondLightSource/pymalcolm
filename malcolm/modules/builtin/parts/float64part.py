from annotypes import Anno

from malcolm.core import (
    AMetaDescription,
    APartName,
    AUnits,
    Display,
    NumberMeta,
    Part,
    PartRegistrar,
    ULimitHigh,
    ULimitLow,
    UPrecision,
)

from ..util import AConfig, AGroup, AWidget, AWriteable, set_tags

with Anno("Initial value of the created attribute"):
    AValue = float

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMetaDescription = AMetaDescription
AUnits = AUnits
ULimitHigh = ULimitHigh
ULimitLow = ULimitLow
UPrecision = UPrecision
AWriteable = AWriteable
AConfig = AConfig
AGroup = AGroup
AWidget = AWidget


class Float64Part(Part):
    """Create a single float64 Attribute on the Block"""

    def __init__(
        self,
        name: APartName,
        description: AMetaDescription,
        writeable: AWriteable = False,
        config: AConfig = 1,
        group: AGroup = None,
        widget: AWidget = None,
        value: AValue = 0.0,
        limit_low: ULimitLow = 0,
        limit_high: ULimitHigh = 0,
        precision: UPrecision = 8,
        units: AUnits = "",
    ) -> None:
        super().__init__(name)
        display = Display(
            limitLow=limit_low, limitHigh=limit_high, precision=precision, units=units
        )
        meta = NumberMeta("float64", description, display=display)
        set_tags(meta, writeable, config, group, widget)
        self.attr = meta.create_attribute_model(value)
        self.writeable_func = self.attr.set_value if writeable else None

    def setup(self, registrar: PartRegistrar) -> None:
        registrar.add_attribute_model(self.name, self.attr, self.writeable_func)
