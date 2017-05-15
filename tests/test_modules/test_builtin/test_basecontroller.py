import unittest
from mock import Mock

from malcolm.modules.builtin.controllers import BasicController


class TestBaseController(unittest.TestCase):
    def test_init(self):
        params = Mock()
        params.mri = "MyMRI"
        params.description = "My description"
        process = Mock()
        o = BasicController(process, [], params)
        assert o.mri == params.mri
        assert o.params is params
        assert o.process is process

