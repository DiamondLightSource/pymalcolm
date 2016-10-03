from malcolm.core.vmeta import VMeta
from malcolm.core.ntscalararray import NTScalarArray


class VArrayMeta(VMeta):
    # intermediate class so TableMeta can say "only arrays"
    attribute_class = NTScalarArray
