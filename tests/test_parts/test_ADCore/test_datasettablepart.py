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
                         ["name", "filename", "type", "path", "uniqueid"])

    def test_post_configure(self):
        task = MagicMock()
        part_info = dict(
            HDF=[
                DatasetProducedInfo(
                    "det", "fn1", "primary", "/p/det", "/p/uid"),
                DatasetProducedInfo(
                    "stat", "fn1", "additional", "/p/s1", "/p/uid"),
                DatasetProducedInfo(
                    "stat", "fn1", "additional", "/p/s2", "/p/uid"),
            ]
        )
        self.o.update_datasets_table(task, part_info)
        v = self.o.datasets.value
        self.assertEqual(v.name, ["det", "stat", "stat"])
        self.assertEqual(v.filename, ["fn1", "fn1", "fn1"])
        self.assertEqual(v.type, ["primary", "additional", "additional"])
        self.assertEqual(v.path, ["/p/det", "/p/s1", "/p/s2"])
        self.assertEqual(v.uniqueid, ["/p/uid", "/p/uid", "/p/uid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
