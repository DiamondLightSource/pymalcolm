from collections import OrderedDict


class Map(OrderedDict):

    def __init__(self, meta, d=None):
        super(Map, self).__init__()

        self._meta = meta

        if d is None:
            d = {}

        for key, value in d.items():
            if key in meta.elements.keys():
                self.__setattr__(key, value)
            else:
                raise KeyError("%s is not a valid key for given meta" % key)

    def __getattr__(self, item):
        """
        Override get attribute to get item from self

        Args:
            item: Attribute to lookup as a key

        Returns:
            Value corresponding to item key
        Raises:
            AttributeError: If KeyError raised by __getitem__
        """

        try:
            return self.__getitem__(item)
        except KeyError:
            # Need to raise AttributeError as OrderedDict expects this
            raise AttributeError

    def __setattr__(self, key, value):
        """
        Override set attribute to check if key is allowed in _meta
        and then set value in self. Use default if _meta doesn't exist

        Args:
            key: Key in self
            value: Value corresponding to key
        Raises:
            KeyError: If key is invalid
        """
        if hasattr(self, "_meta"):
            if key not in self._meta.elements.keys():
                raise KeyError("Map does not have element %s" % key)

            self[key] = value
        else:
            OrderedDict.__setattr__(self, key, value)
