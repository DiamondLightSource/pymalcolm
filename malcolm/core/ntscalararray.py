from .attributemodel import AttributeModel
from .serializable import Serializable


@Serializable.register_subclass("epics:nt/NTScalarArray:1.0")
class NTScalarArray(AttributeModel):
    pass
