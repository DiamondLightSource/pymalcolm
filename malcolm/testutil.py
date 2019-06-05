import unittest

from annotypes import TYPE_CHECKING, Union, Sequence, add_call_types
from mock import MagicMock as Mock, patch

from malcolm.core import Hook, Part, Controller, Process, ProcessPublishHook, \
    APublished, ProcessStartHook, UnpublishedInfo
from malcolm.modules import builtin

if TYPE_CHECKING:
    from typing import List, Any, Type, Callable, Optional


class ChildTestCase(unittest.TestCase):
    @staticmethod
    @patch("malcolm.modules.ca.util.catools", Mock())
    def create_child_block(child_block, process, **params):
        # type: (Callable, Process, **Any) -> Controller
        """Creates an instance of child_block with CA calls mocked out.

        Args:
            child_block (callable): The function to call to get the block
            process (Process): The process to run under
            **params: Parameters to pass to child_block()

        Returns:
            child: The child object with an attribute mock_requests that will
                have a call.put(attr_name, value) or
                a call.post(method_name, params) for anything the child is
                asked to handle
        """
        controllers = child_block(**params)
        for controller in controllers:
            process.add_controller(controller)
            if not isinstance(controller,
                              builtin.controllers.ManagerController):
                # We've already setup the CAParts and added to the block, so we
                # can safely delete them so they don't try to connect
                controller.parts = {}
        child = controllers[-1]
        child.handled_requests = Mock(return_value=None)

        def handle_put(request):
            attr_name = request.path[1]
            # store values sent to the mocked block so that tests can check them
            child.attributes[attr_name] = request.value

            child.handled_requests.put(attr_name, request.value)
            return [request.return_response()]

        def handle_post(request):
            method_name = request.path[1]
            value = child.handled_requests.post(
                method_name, **request.parameters)
            return [request.return_response(value)]

        child._handle_put = handle_put
        child._handle_post = handle_post
        child.attributes = {}
        return child

    def mock_when_value_matches(self, child):
        def handle_when_value_matches_async(attr, good_value, bad_values=None):
            # tell the mock we were called
            child.handled_requests.when_value_matches(
                attr, good_value, bad_values)
            # poke the value we are looking for into the attribute so
            # that old_when_matches will immediately succeed
            # If it's callable then rely on the test code to do this
            if not callable(good_value):
                self.set_attributes(child, **{attr: good_value})
            # now run the original code
            return self.old_when_matches_async(attr, good_value, bad_values)

        def block_view(context=None, old=child.block_view):
            self._context = context
            view = old(context)
            self.old_when_matches_async = object.__getattribute__(
                view, "when_value_matches_async")
            object.__setattr__(view, "when_value_matches_async",
                               handle_when_value_matches_async)
            return view

        child.block_view = block_view
        return child

    def set_attributes(self, child, **params):
        """Set the child's attributes to the give parameter values"""
        for k, v in params.items():
            attr = child._block[k]
            if hasattr(attr.meta, "choices"):
                # Make sure the value is in choices
                if v not in attr.meta.choices:
                    attr.meta.set_choices(list(attr.meta.choices) + [v])
            attr.set_value(v)

    def assert_hooked(self,
                      part,  # type: Part
                      hooks,  # type: Union[Type[Hook], Sequence[Type[Hook]]]
                      func,  # type: Callable[..., Any]
                      args_gen=None  # type: Optional[Callable[(), List[str]]]
                      ):
        if args_gen is None:
            args_gen = getattr(func, "call_types", {}).keys
        if not isinstance(hooks, Sequence):
            hooks = [hooks]
        for hook in hooks:
            assert part.hooked[hook] == (func, args_gen)


class PublishController(Controller):
    published = []

    def on_hook(self, hook):
        if isinstance(hook, ProcessPublishHook):
            hook(self.do_publish)

    @add_call_types
    def do_publish(self, published):
        # type: (APublished) -> None
        self.published = published


class UnpublishableController(Controller):
    def on_hook(self, hook):
        if isinstance(hook, ProcessStartHook):
            hook(self.on_start)

    def on_start(self):
        return UnpublishedInfo(self.mri)
