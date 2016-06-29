from malcolm.core.controller import Controller
from malcolm.core.attribute import Attribute
from malcolm.core.numbermeta import NumberMeta
from malcolm.core.method import takes

import numpy as np


class CounterController(Controller):

    def create_attributes(self):
        self.counter = Attribute(NumberMeta("counter", "A counter", np.int32))
        self.counter.set_put_function(self.counter.set_value)
        self.counter.set_value(0)
        yield self.counter

    @takes()
    def reset(self):
        self.counter.set_value(0)
        self.block.notify_subscribers()

    @takes()
    def increment(self):
        self.counter.set_value(self.counter.value + 1)
        self.block.notify_subscribers()
