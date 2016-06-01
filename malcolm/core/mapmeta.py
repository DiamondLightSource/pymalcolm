from collections import OrderedDict

from loggable import Loggable
from malcolm.core.attributemeta import AttributeMeta


class MapMeta(Loggable):
    """An object containing a set of AttributeMeta objects"""

    def __init__(self, name):
        super(MapMeta, self).__init__(logger_name=name)

        self.name = name
        self.elements = OrderedDict()
        self.required = []

    def add_element(self, attribute_meta, required=False):
        """
        Add an element and whether it is required.

        Args:
            attribute_meta(AttributeMeta): Attribute instance to store
            required(bool): Whether attribute is required or optional

        Raises:
            ValueError:
        """

        if attribute_meta.name in self.elements.keys():
            raise ValueError("Element already exists in dictionary")
        else:
            self.elements[attribute_meta.name] = attribute_meta
            self.required.append(required)
