from annotypes import Anno, WithCallTypes, Array, to_array, Union, Sequence

with Anno("The scannable axes, e.g. ['x', 'y'] or 'x'"):
    Axes = Array[str]
with Anno("The first point to be generated, e.g. [0., 2.4] or 1."):
    Start = Array[float]
with Anno("The final point to be generated, e.g. [-8., 6.4] or 5."):
    Stop = Array[float]
with Anno("The number of points to generate, e.g. 5"):
    Size = int
with Anno("The scannable units, e.g. ['mm', 'deg'] or 'mm'"):
    Units = Array[str]
with Anno("Whether to reverse on alternate runs"):
    Alternate = bool

def_units = Units("mm")


class ManyArgs(WithCallTypes):
    def __init__(self,
                 axes: Union[Axes, Sequence[str], str],
                 start: Union[Start, Sequence[float], float],
                 stop: Union[Stop, Sequence[float], float],
                 size: Size,
                 units: Union[Units, Sequence[str], str] = def_units,
                 alternate: Alternate = False):
        self.axes = Axes(axes)
        self.start = Start(start)
        self.stop = Stop(stop)
        self.size = size
        self.units = Units(units)
        self.alternate = alternate
        assert len(self.axes) == len(self.units) == \
            len(self.start) == len(self.stop), \
            "axes %s, units %s, start %s, stop %s are not the same length" % (
                self.axes, self.units, self.start, self.stop)
