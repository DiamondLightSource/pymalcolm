import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

from collections import OrderedDict

import unittest
from mock import MagicMock, call, patch

# module imports
from malcolm.core import Block, Attribute
from malcolm.core.vmetas import NumberMeta


class TestBlock(unittest.TestCase):

    def test_init(self):
        b = Block()
        self.assertEqual(list(b), [])
        self.assertEqual("malcolm:core/Block:1.0", b.typeid)

    def test_getattr(self):
        b = Block()
        a = Attribute(NumberMeta("int32"))
        b.replace_endpoints(dict(a=a))
        def f(meta, value):
            a.set_value(value)
        b.set_writeable_functions(dict(a=f))
        b.a = 32
        self.assertEqual(b.a, 32)




if __name__ == "__main__":
    unittest.main(verbosity=2)
