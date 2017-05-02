from .vmeta import VMeta
from .ntscalararray import NTScalarArray


class VArrayMeta(VMeta):
    # intermediate class so TableMeta can say "only arrays"
    attribute_class = NTScalarArray
