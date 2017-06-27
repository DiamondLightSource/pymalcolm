import unittest
from mock import Mock

from malcolm.core import call_with_params
from malcolm.modules.demo.blocks import hello_block, counter_block, ticker_block


class TestBuiltin(unittest.TestCase):
    def test_hello_block(self):
        process = Mock()
        controller = call_with_params(hello_block, process, mri="my_mri")
        assert list(controller.block_view()) == [
            'meta', 'health', 'error', 'greet']

    def test_counter_block(self):
        process = Mock()
        controller = call_with_params(counter_block, process, mri="my_mri")
        assert list(controller.block_view()) == [
            'meta', 'health', 'counter', 'increment', 'zero']

    def test_ticker_block(self):
        process = Mock()
        controller = call_with_params(
            ticker_block, process, mri="my_mri", configDir="/tmp")
        assert list(controller.block_view()) == [
             'meta',
             'health',
             'state',
             'layout',
             'design',
             'exports',
             'modified',
             'completedSteps',
             'configuredSteps',
             'totalSteps',
             'axesToMove',
             'abort',
             'configure',
             'disable',
             'pause',
             'reset',
             'resume',
             'run',
             'save',
             'validate']
