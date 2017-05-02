from .attributemodel import AttributeModel
from .serializable import Serializable


@Serializable.register_subclass("epics:nt/NTUnion:1.0")
class NTUnion(AttributeModel):
    pass
