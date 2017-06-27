from .attributemodel import AttributeModel
from .serializable import Serializable


@Serializable.register_subclass("epics:nt/NTScalar:1.0")
class NTScalar(AttributeModel):
    pass
