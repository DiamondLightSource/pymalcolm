from .meta import Meta
from .serializable import Serializable


@Serializable.register_subclass("malcolm:core/BlockMeta:1.0")
class BlockMeta(Meta):
    pass
