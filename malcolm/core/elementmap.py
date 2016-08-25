from collections import OrderedDict

from malcolm.compat import str_
from malcolm.core.monitorable import Monitorable
from malcolm.core.serializable import serialize_object, Serializable, \
    deserialize_object
from malcolm.core.vmeta import VMeta


@Serializable.register_subclass("malcolm:core/ElementMap:1.0")
class ElementMap(Monitorable):

    child_type_check = VMeta

    def __init__(self, d=None):
        if d:
            self.replace_endpoints(d)

    def replace_endpoints(self, d):
        children = OrderedDict()

        for k, v in d.items():
            assert isinstance(k, str_), "Expected string, got %s" % (k,)
            if k == "typeid":
                assert v == self.typeid, \
                    "Dict has typeid %s but Class has %s" % (v, self.typeid)
            else:
                try:
                    object.__getattribute__(self, k)
                except AttributeError:
                    children[k] = deserialize_object(v, self.child_type_check)
                else:
                    raise AttributeError(
                        "Setting child %r would shadow an attribute" % (k,))

        self.endpoints = list(children)

        for k, v in children.items():
            self.set_endpoint_data(k, v, notify=False)

        self.report_changes([[], serialize_object(self)])
