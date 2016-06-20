from malcolm.core.controller import Controller
from malcolm.core.attribute import Attribute
from malcolm.core.numbermeta import NumberMeta
from malcolm.core.mapmeta import MapMeta
from malcolm.core.method import Method, takes

import numpy as np

class CounterController(Controller):

    def __init__(self, block):
        super(CounterController, self).__init__(block)
        self.counter = Attribute("counter",
                                 NumberMeta("counter", "A counter", np.int32))
        self.counter.set_value(0)

    @takes()
    def reset(self):
        self.counter.set_value(0)

    @takes()
    def increment(self):
        self.counter.set_value(self.counter.value + 1)
