from annotypes import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Dict, Any, List


def submodule_all(globals_d, only_classes=True):
    # type: (Dict[str, Any]) -> List[str]
    # Return all the classes
    return sorted(k for k, v in globals_d.items()
                  if not only_classes or isinstance(v, type))

