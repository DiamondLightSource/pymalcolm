import unittest
import functools
from mock import Mock, patch

from malcolm.core import call_with_params


class ChildTestCase(unittest.TestCase):
    @patch("malcolm.modules.ca.parts.capart.CAPart.reset", Mock)
    @patch("malcolm.modules.ca.parts.catoolshelper.CaToolsHelper._instance",
           Mock)
    def create_child_block(self, child_block, process, **params):
        """Creates an instance of child_block with CA calls mocked out.

        Args:
            child_block (callable): The function to call to get the block
            process (Process): The process to run under
            **params: Parameters to pass to child_block()

        Returns:
            child: The child object with an attribute mock_writes that will have
                a call(attr_name, value) or call(method_name, params) for
                anything the child is asked to do
        """
        child = call_with_params(child_block, process, **params)
        child.mock_writes = Mock(return_value=None)
        for k in child._write_functions:
            child._write_functions[k] = functools.partial(child.mock_writes, k)
        return child

