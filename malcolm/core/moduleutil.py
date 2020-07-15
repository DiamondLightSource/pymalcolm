from typing import Any, Dict, List


def submodule_all(globals_d, only_classes: Dict[str, Any] = True) -> List[str]:
    # Return all the classes
    return sorted(
        k for k, v in globals_d.items() if not only_classes or isinstance(v, type)
    )
