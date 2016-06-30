from malcolm.core.attributemeta import AttributeMeta
from malcolm.core.serializable import Serializable
from malcolm.compat import base_string

import numpy


@Serializable.register("malcolm:core/Byte:1.0", numpy.int8)
@Serializable.register("malcolm:core/UByte:1.0", numpy.uint8)
@Serializable.register("malcolm:core/Short:1.0", numpy.int16)
@Serializable.register("malcolm:core/UShort:1.0", numpy.uint16)
@Serializable.register("malcolm:core/Int:1.0", numpy.int32)
@Serializable.register("malcolm:core/UInt:1.0", numpy.uint32)
@Serializable.register("malcolm:core/Long:1.0", numpy.int64)
@Serializable.register("malcolm:core/ULong:1.0", numpy.uint64)
@Serializable.register("malcolm:core/Float:1.0", numpy.float32)
@Serializable.register("malcolm:core/Double:1.0", numpy.float64)
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

    def to_dict(self):
        d = super(NumberMeta, self).to_dict()
        return d

    @classmethod
    def from_dict(self, name, d, *args):
        number_meta = NumberMeta(name, d["description"], *args)
        return number_meta
