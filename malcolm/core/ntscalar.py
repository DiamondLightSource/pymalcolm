from malcolm.core.attribute import Attribute
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("epics:nt/NTScalar:1.0")
class NTScalar(Attribute):
    pass
