import inspect
from typing import Dict, List, Mapping, Optional, Sequence, Type, TypeVar

from malcolm.compat import OrderedDict

from .errors import BadValueError

PartInfo = Mapping[str, Optional[Sequence]]

T = TypeVar("T", bound="Info")


class Info:
    """Base class that should be inherited from when a part needs to return
    something from a hooked function"""

    def __repr__(self):
        spec = inspect.getfullargspec(self.__init__)
        args = ", ".join(repr(getattr(self, x)) for x in spec.args[1:])
        return "%s(%s)" % (self.__class__.__name__, args)

    @classmethod
    def filter_parts(cls: Type[T], part_info: PartInfo) -> Dict[str, List[T]]:
        """Filter the part_info dict looking for instances of our class

        Args:
            part_info (dict): {part_name: [Info] or None} as returned from
                Controller.run_hook()

        Returns:
            dict: {part_name: [info]} where info is a subclass of cls
        """
        filtered = OrderedDict()
        for part_name, info_list in part_info.items():
            if info_list is None or isinstance(info_list, Exception):
                continue
            info_list = [i for i in info_list if isinstance(i, cls)]
            if info_list:
                filtered[part_name] = info_list
        return filtered

    @classmethod
    def filter_values(cls: Type[T], part_info: PartInfo) -> List[T]:
        """Filter the part_info dict list looking for instances of our class

        Args:
            part_info (dict): {part_name: [Info] or None} as returned from
                Controller.run_hook()

        Returns:
            list: [info] where info is a subclass of cls
        """
        filtered: List[T] = []
        info_list: Sequence
        assert hasattr(cls, "filter_parts"), "Class has no filter parts method"
        for info_list in cls.filter_parts(part_info).values():
            filtered += info_list
        return filtered

    @classmethod
    def filter_single_value(
        cls: Type[T], part_info: PartInfo, error_msg: str = None
    ) -> T:
        """Filter the part_info dict list looking for a single instance of our
        class

        Args:
            part_info (dict): {part_name: [Info] or None} as returned from
                Controller.run_hook()
            error_msg (str): Optional specific error message to show if
                there isn't a single value

        Returns:
            info subclass of cls
        """
        assert hasattr(cls, "filter_values"), "Class has no filter values method"
        filtered: List[T] = cls.filter_values(part_info)
        if len(filtered) != 1:
            if error_msg is None:
                error_msg = "Expected a single %s, got %s of them" % (
                    cls.__name__,
                    len(filtered),
                )
            raise BadValueError(error_msg)
        return filtered[0]
