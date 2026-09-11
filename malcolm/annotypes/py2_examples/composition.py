from annotypes import add_call_types, WithCallTypes, Anno, Array, Optional
from .simple import Simple, Exposure, Path


with Anno("The path prefix for the list of writers"):
    Prefix = str
with Anno("An array of simple objects"):
    SimpleArray = Array[Simple]


@add_call_types
def composition_func(exposure, prefix=None):
    # type: (Exposure, Prefix) -> Optional[SimpleArray]
    if prefix:
        ret = [Simple(exposure, prefix + suff) for suff in ["/one", "/two"]]
        return SimpleArray(ret)
    else:
        return None


class CompositionClass(WithCallTypes):
    def __init__(self, exposure, path):
        # type: (Exposure, Path) -> None
        self.exposure = exposure
        self.path = path
        self.child = Simple(exposure, path)

    def write_hello(self):
        self.child.write_data("hello")
