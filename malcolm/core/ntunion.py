from malcolm.core.attribute import Attribute
from malcolm.core.serializable import Serializable


@Serializable.register_subclass("epics:nt/NTUnion:1.0")
class NTUnion(Attribute):
    pass
