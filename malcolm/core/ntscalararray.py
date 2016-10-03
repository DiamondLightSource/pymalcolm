from malcolm.core.attribute import Attribute
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("epics:nt/NTScalarArray:1.0")
class NTScalarArray(Attribute):
    pass
