from collections import OrderedDict

import numpy as np

from malcolm.core import RunnableDeviceStateMachine, REQUIRED, method_returns, \
    method_only_in, method_takes, ElementMap, Attribute
from malcolm.core.vmetas import PointGeneratorMeta, StringArrayMeta, NumberMeta
from malcolm.controllers.builtin.defaultcontroller import DefaultController


sm = RunnableDeviceStateMachine

configure_args = [
    "generator", PointGeneratorMeta("Generator instance"), REQUIRED,
    "axes_to_move", StringArrayMeta("Axes that should be moved"), REQUIRED,
    "exposure", NumberMeta("float64", "How long to remain at each point"),
    REQUIRED]


@sm.insert
@method_takes()
class ManagerController(DefaultController):
    """RunnableDevice implementer that also exposes GUI for child parts"""
    # default attributes
    totalSteps = None
    currentStep = None
    exposure = None
    generator = None
    iterator = None
    points = None

    def get_point(self, num):
        npoints = len(self.points)
        if num >= npoints:
            # Generate some more points and cache them
            for i in range(num - npoints + 1):
                self.points.append(next(self.iterator))
        return self.points[num]

    def create_attributes(self):
        self.totalSteps = Attribute(NumberMeta(
            "int32", "Readback of number of scan steps"), 0)
        yield "totalSteps", self.totalSteps, None
        self.currentStep = Attribute(NumberMeta(
            "int32", "Readback of number of scan steps"), 0)
        yield "currentStep", self.currentStep, None

    def something_create_methods(self):
        # Look for all parts that hook into the validate method
        validate_funcs = self.Validating.find_hooked_functions(self.parts)
        takes_elements = OrderedDict()
        defaults = OrderedDict()
        for part_name, func in validate_funcs.items():
            self.log_debug("Adding validating parameters from %s", part_name)
            takes_elements.update(func.MethodMeta.takes.to_dict())
            defaults.update(func.MethodMeta.defaults)
        takes = ElementMap(takes_elements)

        # Decorate validate and configure with the sum of its parts
        # No need to copy as the superclass _set_block_children does this
        self.validate.MethodMeta.set_takes(takes)
        self.validate.MethodMeta.set_returns(takes)
        self.validate.MethodMeta.set_defaults(defaults)
        self.configure.MethodMeta.set_takes(takes)
        self.validate.MethodMeta.set_defaults(defaults)

        return super(ManagerController, self).create_methods()

    @method_takes(*configure_args)
    @method_returns(*configure_args)
    def validate(self, params, _):
        self.do_validate(params)
        return params

    def do_validate(self, params):
        raise NotImplementedError()

    @method_only_in(sm.IDLE)
    @method_takes(*configure_args)
    def configure(self, params):
        try:
            self.transition(sm.CONFIGURING, "Configuring", create_tasks=True)
            self.exposure = params.exposure
            self.generator = params.generator
            self.points = []
            self.iterator = params.generator.iterator()
            self.currentStep.set_value(0)
            steps = np.prod(params.generator.index_dims)
            self.totalSteps.set_value(steps)
            self.do_configure(params)
            self.transition(sm.READY, "Done configuring")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Configuring")
            self.transition(sm.FAULT, str(e))
            raise

    def do_configure(self, params):
        raise NotImplementedError()

    @method_only_in(sm.READY)
    def run(self):
        try:
            self.transition(sm.PRERUN, "Preparing for run", create_tasks=True)
            next_state = self.do_run()
            self.transition(next_state, "Run finished")
        except Exception as e:  # pylint:disable=broad-except
            self.log_exception("Fault occurred while Running")
            self.transition(sm.FAULT, str(e))
            raise

    def do_run(self):
        raise NotImplementedError()








