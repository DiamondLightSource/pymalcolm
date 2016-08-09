from malcolm.core.elementmap import ElementMap
from malcolm.core.serializable import Serializable
from malcolm.core.varraymeta import VArrayMeta


@Serializable.register_subclass("malcolm:core/TableElementMap:1.0")
class TableElementMap(ElementMap):
    child_type_check = VArrayMeta
