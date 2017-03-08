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

    def set_endpoint_data(self, name, value):
        name = deserialize_object(name, str_)
        if name == "meta":
            value = deserialize_object(value, BlockMeta)
        else:
            value = deserialize_object(value, (AttributeModel, MethodModel))
        return super(BlockModel, self).set_endpoint_data(name, value)

    def set_endpoint_data_locked(self, name, value):
        if name not in self.endpoints:
            self.endpoints.append(name)
        super(BlockModel, self).set_endpoint_data_locked(name, value)

    def remove_endpoint(self, name):
        if self.notifier:
            self.notifier.make_endpoint_change(
                self.remove_endpoint_locked, self.path + [name])
        else:
            self.remove_endpoint_locked(name)

    def remove_endpoint_locked(self, name):
        self.endpoints.remove(name)
        delattr(self, name)
