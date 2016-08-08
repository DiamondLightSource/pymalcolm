from malcolm.core import Attribute, method_takes, Controller
from malcolm.core.vmetas import NumberMeta


@method_takes()
class CounterController(Controller):

    def create_attributes(self):
        self.counter = Attribute(
            NumberMeta("uint32", "A counter"), 0)
        yield "counter", self.counter, self.counter.set_value

    @Controller.Resetting
    def do_reset(self):
        self.counter.set_value(0)

    @method_takes()
    def increment(self):
        self.counter.set_value(self.counter.value + 1)
