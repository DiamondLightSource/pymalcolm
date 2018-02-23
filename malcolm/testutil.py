import unittest
from mock import MagicMock as Mock, patch


class ChildTestCase(unittest.TestCase):
    @patch("malcolm.modules.ca.util.CaToolsHelper._instance", Mock())
    def create_child_block(self, child_block, process, **params):
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
            # We've already setup the CAParts and added to the block, so we
            # can safely delete them so they don't try to connect
            controller.parts = {}
            process.add_controller(controller)
        child = controllers[-1]
        child.handled_requests = Mock(return_value=None)

        def handle_put(request):
            attr_name = request.path[1]
            child.handled_requests.put(attr_name, request.value)
            return [request.return_response()]

        def handle_post(request):
            method_name = request.path[1]
            child.handled_requests.post(method_name, **request.parameters)
            return [request.return_response()]

        child._handle_put = handle_put
        child._handle_post = handle_post
        return child

    def set_attributes(self, child, **params):
        """Set the child's attributes to the give parameter values"""
        for k, v in params.items():
            child._block[k].set_value(v)
