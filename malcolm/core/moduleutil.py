from typing import Any, Dict, List, Union


def submodule_all(
    globals_d, only_classes: Union[Dict[str, Any], bool] = True
) -> List[str]:
    # Return all the classes
    return sorted(
        k for k, v in globals_d.items() if not only_classes or isinstance(v, type)
    )
