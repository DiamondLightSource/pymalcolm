from malcolm.core.attributemeta import AttributeMeta
from malcolm.compat import base_string

import numpy


@AttributeMeta.register_subclass("malcolm:core/Byte:1.0", numpy.int8)
@AttributeMeta.register_subclass("malcolm:core/UByte:1.0", numpy.uint8)
@AttributeMeta.register_subclass("malcolm:core/Short:1.0", numpy.int16)
@AttributeMeta.register_subclass("malcolm:core/UShort:1.0", numpy.uint16)
@AttributeMeta.register_subclass("malcolm:core/Int:1.0", numpy.int32)
@AttributeMeta.register_subclass("malcolm:core/UInt:1.0", numpy.uint32)
@AttributeMeta.register_subclass("malcolm:core/Long:1.0", numpy.int64)
@AttributeMeta.register_subclass("malcolm:core/ULong:1.0", numpy.uint64)
@AttributeMeta.register_subclass("malcolm:core/Float:1.0", numpy.float32)
@AttributeMeta.register_subclass("malcolm:core/Double:1.0", numpy.float64)
class NumberMeta(AttributeMeta):
    """Meta object containing information for a numerical value"""

    def __init__(self, name, description, dtype):
        super(NumberMeta, self).__init__(name, description, dtype)
        self.dtype = dtype

    def validate(self, value):
        if value is None:
            return None
        cast = self.dtype(value)
        if not isinstance(value, base_string):
            assert cast == value, \
                "Lost information converting %s to %s" % (value, cast)
        return cast

    def attribute_type(self):
        return AttributeMeta.SCALAR

    def to_dict(self):
        d = super(NumberMeta, self).to_dict()
        return d

    @classmethod
    def from_dict(self, name, d, *args):
        number_meta = NumberMeta(name, d["description"], *args)
        return number_meta
