import unittest
from mock import Mock

from malcolm.core import call_with_params
from malcolm.modules.builtin.blocks import proxy_block


class TestBuiltin(unittest.TestCase):
    def test_proxy_block(self):
        process = Mock()
        controller = call_with_params(
            proxy_block, process, comms="comms_mri", mri="my_mri", publish=True)
        process.add_controller.assert_called_once_with(
            "my_mri", controller, True)
        process.get_controller.assert_called_once_with("comms_mri")
        assert controller.client_comms == process.get_controller.return_value
