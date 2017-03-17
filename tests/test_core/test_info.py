import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import setup_malcolm_paths

import unittest
from mock import Mock
from collections import OrderedDict

from malcolm.core.info import Info
from malcolm.core import Part, method_takes


class MyPart(Part, Info):
    @method_takes()
    def foo(self):
        pass


class TestInit(unittest.TestCase):

    def setUp(self):
        process = Mock()
        self.d1 = {'a': 'xyzzy', 'b': None}
        self.d2 = {'a': 'xyzzy',
                   'b': [ MyPart(process, 'name1') ],
                   'c': [ MyPart(process, 'name2') ],
                   'd': 'x'}
        pass

    def test_filter_parts(self):
        filtered = MyPart.filter_parts(self.d1)
        self.assertEqual(len(filtered), 0)
        filtered = MyPart.filter_parts(self.d2)
        self.assertEqual(len(filtered), 2)

        self.assertEqual(filtered['c'][0].name, 'name2')

    def test_filer_values(self):
        filtered = MyPart.filter_values(self.d1)
        self.assertEqual(len(filtered), 0)
        filtered = MyPart.filter_values(self.d2)
        self.assertEqual(len(filtered), 2)

        self.assertEqual(filtered[0].name, 'name2')

