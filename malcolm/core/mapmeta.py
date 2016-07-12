from collections import OrderedDict

from malcolm.core.notifier import Notifier
from malcolm.core.serializable import Serializable

OPTIONAL = object()
REQUIRED = object()


@Serializable.register_subclass("malcolm:core/MapMeta:1.0")
class MapMeta(Notifier):
    """An object containing a set of ScalarMeta objects"""

    def __init__(self, name, description):
        super(MapMeta, self).__init__(name)
        self.description = description
        self.elements = OrderedDict()
        self.required = []
        self.tags = []

    def add_element(self, attribute_meta, required=False):
        """
        Add an element and whether it is required.

        Args:
            attribute_meta(ScalarMeta): Attribute instance to store
            required(bool): Whether attribute is required or optional

        Raises:
            ValueError: Element already exists in dictionary
        """

        if attribute_meta.name in self.elements.keys():
            raise ValueError("Element already exists in dictionary")
        else:
            self.elements[attribute_meta.name] = attribute_meta
            if required:
                self.required.append(attribute_meta.name)

    def validate(self, d):
        """
        Check if the elements in the given dictionary are valid

        Args:
            d(dict): Dictionary to check

        Returns:
            dict: Given dictionary, if valid
        Raises:
            KeyError: If dictionary not valid
        """

        for element in d.keys():
            if element not in self.elements.keys():
                raise KeyError("%s is not a valid element" % element)

        for element in self.required:
            if element not in d.keys():
                raise KeyError("Required element %s is missing" % element)

        return d

    def to_dict(self):
        """Convert object attributes into a dictionary"""

        d = OrderedDict()
        element_dict = OrderedDict()
        for element_name, meta in self.elements.items():
            element_dict[element_name] = meta.to_dict()
        d['typeid'] = self.typeid
        d['elements'] = element_dict
        d['description'] = self.description
        d['tags'] = self.tags
        d['required'] = self.required

        return d

    @classmethod
    def from_dict(cls, name, d):
        """Create a MapMeta instance from the serialized version of itself

        Args:
            name (str): MapMeta instance name
            d (dict): Something that self.to_dict() would create
        """
        map_meta = cls(name, d["description"])
        for ename, element in d["elements"].items():
            attribute_meta = Serializable.from_dict(ename, element)
            map_meta.add_element(attribute_meta, ename in d["required"])
        map_meta.tags = d["tags"]
        return map_meta

