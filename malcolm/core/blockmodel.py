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

    def set_notifier_path(self, notifier, path):
        super(BlockModel, self).set_notifier_path(notifier, path)
        for endpoint in self.endpoints:
            self[endpoint].set_notifier_path(notifier, self.path + [endpoint])

    def set_endpoint_data(self, name, value):
        name = deserialize_object(name, str_)
        if name == "meta":
            value = deserialize_object(value, BlockMeta)
        else:
            value = deserialize_object(value, (AttributeModel, MethodModel))
        with self.notifier.changes_squashed:
            if name in self.endpoints:
                # Stop the old endpoint notifying
                self[name].set_notifier_path(Model.notifier, ())
            else:
                self.endpoints.append(name)
            value.set_notifier_path(self.notifier, self.path + [name])
            setattr(self, name, value)
            # Tell the notifier what changed
            self.notifier.add_squashed_change(self.path + [name], value)
            self._update_fields()
        return value

    def _update_fields(self):
        self.meta.set_fields([x for x in self.endpoints if x != "meta"])

    def remove_endpoint(self, name):
        with self.notifier.changes_squashed:
            self[name].set_notifier_path(Model.notifier, ())
            self.endpoints.remove(name)
            delattr(self, name)
            self._update_fields()
            self.notifier.add_squashed_change(self.path + [name])
