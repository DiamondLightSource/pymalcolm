import sys

from typing import (
    TYPE_CHECKING, TypeVar, Sequence, Union, Optional, Generic,
    overload, Mapping, Any
)
if sys.version_info >= (3, 7):
    from abc import ABCMeta as GenericMeta
    from collections.abc import Mapping as MappingOrigin
    NEW_TYPING = True
else:
    from typing import GenericMeta, Mapping as MappingOrigin
    NEW_TYPING = False
