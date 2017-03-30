import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import setup_malcolm_paths

import unittest
from mock import MagicMock

from malcolm.parts.ADCore.datasettablepart import DatasetTablePart, \
    DatasetProducedInfo


class TestDatasetReportingPart(unittest.TestCase):

    def setUp(self):
        self.process = MagicMock()
        self.child = MagicMock()
        self.params = MagicMock()
        self.o = DatasetTablePart(self.process, self.params)
        list(self.o.create_attributes())

    def test_init(self):
        self.assertEqual(self.o.datasets.meta.elements.endpoints,
                         ["name", "filename", "type", "rank", "path", "uniqueid"])

    def test_post_configure(self):
        task = MagicMock()
        part_info = dict(
            HDF=[
                DatasetProducedInfo(
                    "det.data", "fn1", "primary", 2, "/p/det", "/p/uid"),
                DatasetProducedInfo(
                    "det.sum", "fn1", "secondary", 0, "/p/s1", "/p/uid"),
                DatasetProducedInfo(
                    "det.min", "fn1", "secondary", 0, "/p/s2", "/p/uid"),
            ]
        )
        self.o.update_datasets_table(task, part_info)
        v = self.o.datasets.value
        self.assertEqual(v.name, ("det.data", "det.sum", "det.min"))
        self.assertEqual(v.filename, ("fn1", "fn1", "fn1"))
        self.assertEqual(v.type, ("primary", "secondary", "secondary"))
        self.assertEqual(list(v.rank), [2, 0, 0])
        self.assertEqual(v.path, ("/p/det", "/p/s1", "/p/s2"))
        self.assertEqual(v.uniqueid, ("/p/uid", "/p/uid", "/p/uid"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
