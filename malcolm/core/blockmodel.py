from malcolm.compat import str_

from .attributemodel import AttributeModel
from .blockmeta import BlockMeta
from .methodmodel import MethodModel
from .model import Model
from .serializable import Serializable, deserialize_object


@Serializable.register_subclass("malcolm:core/Block:1.0")
class BlockModel(Model):
    """Data Model for a Block"""

    def __init__(self):
        # TODO: how do we take children while preserving order?
        self.endpoints = []
        self.meta = self.set_endpoint_data("meta", BlockMeta())

    def set_endpoint_data(self, name, value):
        name = deserialize_object(name, str_)
        if name == "meta":
            value = deserialize_object(value, BlockMeta)
        else:
            value = deserialize_object(value, (AttributeModel, MethodModel))
        return super(BlockModel, self).set_endpoint_data(name, value)

    def _update_fields(self):
        self.meta.set_fields([x for x in self.endpoints if x != "meta"])

    def set_endpoint_data_locked(self, name, value):
        if name not in self.endpoints:
            self.endpoints.append(name)
        ret = super(BlockModel, self).set_endpoint_data_locked(name, value)
        self._update_fields()
        return ret

    def remove_endpoint(self, name):
        if self.notifier:
            self.notifier.make_endpoint_change(
                self.remove_endpoint_locked, self.path + [name])
        else:
            self.remove_endpoint_locked(name)

    def remove_endpoint_locked(self, name):
        self.endpoints.remove(name)
        delattr(self, name)
        self._update_fields()
