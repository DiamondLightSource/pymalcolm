import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock, call

# logging
# import logging
# logging.basicConfig(level=logging.DEBUG)

# module imports
from malcolm.core.controller import Controller


class TestController(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.c = Controller('block', MagicMock())
        self.b = self.c.block

    def test_init(self):
        self.c.process.add_block.assert_called_once_with(self.b)
        self.assertEqual({}, self.c.parts)

        self.assertEqual(
            self.b["state"].meta.typeid, "malcolm:core/ChoiceMeta:1.0")
        self.assertEqual(self.b.state, "Disabled")
        self.assertEqual(
            self.b["status"].meta.typeid, "malcolm:core/StringMeta:1.0")
        self.assertEqual(self.b.status, "Disabled")
        self.assertEqual(
            self.b["busy"].meta.typeid, "malcolm:core/BooleanMeta:1.0")
        self.assertEqual(self.b.busy, False)

    def test_set_writeable_methods(self):
        m = MagicMock()
        m.name = "configure"
        self.c.register_method_writeable(m, "Ready")
        self.assertEqual(self.c.methods_writeable['Ready'][m], True)

    def test_run_hook(self):
        # TODO: write this
        pass

    def test_run_hook_raises(self):
        # TODO: write this
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
