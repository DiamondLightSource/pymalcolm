from malcolm.compat import str_
from .controller import Controller
from .hook import get_hook_decorated
from .hookrunner import HookRunner
from .loggable import Loggable
from .methodmodel import get_method_decorated, MethodModel


class Part(Loggable):
    def __init__(self, name):
        super(Part, self).__init__()
        assert isinstance(name, str_), \
            "Expected name to be a string, got %s. Did you forget to " \
            "subclass __init__ in %s?" % (name, self)
        self.controller = None
        self.use_cothread = False
        self.process = None
        self.name = name
        self.method_models = {}

    def notify_dispatch_request(self, request):
        """Will be called when a context passed to a hooked function is about
        to dispatch a request"""
        pass

    def attach_to_controller(self, controller):
        """Attach this part to a controller

        Args:
            controller (Controller): The controller to attach to
        """
        self.set_logger_extra(mri=controller.mri, part=self.name)
        self.controller = controller
        self.process = controller.process
        self.use_cothread = controller.use_cothread

    def spawn(self, func, *args, **kwargs):
        """Spawn a function in the right thread"""
        spawned = self.process.spawn(func, args, kwargs, self.use_cothread)
        return spawned

    def update_part_health(self, alarm=None):
        """Set the health attribute"""
        self.controller.update_health(self, alarm)

    def make_hook_runner(self, hook_queue, func_name, context, *args, **params):
        # TODO: add phase information
        func = getattr(self, func_name)
        method_model = self.method_models.get(func_name, MethodModel())
        filtered_params = {k: v for k, v in params.items()
                           if k in method_model.takes.elements}
        args += method_model.prepare_call_args(**filtered_params)
        runner = HookRunner(hook_queue, self, func, context, args)
        return runner

    def create_method_models(self):
        hooked = [name for (name, _, _) in get_hook_decorated(self)]
        for name, method_model, func in get_method_decorated(self):
            self.method_models[name] = method_model
            if name not in hooked:
                yield name, method_model, func

    def create_attribute_models(self):
        """Should be implemented in subclasses to yield any Attributes that
        should be attached to the Block

        Yields:
            tuple: (attribute_name, attribute, set_function), where:

                - attribute_name is the name of the Attribute within the Block
                - attribute is the Attribute to be attached
                - set_function is a callable if the Attribute should be
                  writeable, or None if not
        """
        return iter(())

