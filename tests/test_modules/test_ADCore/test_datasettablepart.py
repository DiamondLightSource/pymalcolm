import unittest
from mock import ANY

from malcolm.core import call_with_params
from malcolm.modules.ADCore.parts import DatasetTablePart
from malcolm.modules.ADCore.infos import DatasetProducedInfo


class TestDatasetReportingPart(unittest.TestCase):

    def setUp(self):
        self.o = call_with_params(DatasetTablePart, name="n")
        list(self.o.create_attributes())

    def test_init(self):
        assert list(self.o.datasets.meta.elements) == (
                         ["name", "filename", "type", "rank", "path", "uniqueid"])

    def test_post_configure(self):
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
        self.o.update_datasets_table(ANY, part_info)
        v = self.o.datasets.value
        assert v.name == ("det.data", "det.sum", "det.min")
        assert v.filename == ("fn1", "fn1", "fn1")
        assert v.type == ("primary", "secondary", "secondary")
        assert list(v.rank) == [2, 0, 0]
        assert v.path == ("/p/det", "/p/s1", "/p/s2")
        assert v.uniqueid == ("/p/uid", "/p/uid", "/p/uid")
