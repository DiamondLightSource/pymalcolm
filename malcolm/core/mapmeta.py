from collections import OrderedDict

from loggable import Loggable
from malcolm.core.attributemeta import AttributeMeta


class MapMeta(Loggable):
    """A meta object to store a set of attribute metas"""

    def __init__(self, name):
        super(MapMeta, self).__init__(logger_name=name)

        self.name = name
        self.elements = OrderedDict({})

    def add_element(self, attribute_meta, required=False):
        """
        Add an element, stating whether it is required.

        Args:
            attribute_meta(AttributeMeta): Attribute instance to store
            required(bool): Whether attribute is required or optional
        """

        self.elements[attribute_meta.name] = (attribute_meta, required)
