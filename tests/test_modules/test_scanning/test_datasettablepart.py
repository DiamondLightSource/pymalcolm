import unittest

from mock import MagicMock

from malcolm.modules.scanning.infos import DatasetProducedInfo
from malcolm.modules.scanning.parts import DatasetTablePart
from malcolm.modules.scanning.util import DatasetType


class TestDatasetReportingPart(unittest.TestCase):
    def setUp(self):
        self.r = MagicMock()
        self.o = DatasetTablePart(name="n")
        self.o.setup(self.r)

    def test_init(self):
        assert list(self.o.datasets.meta.elements) == (
            ["name", "filename", "type", "rank", "path", "uniqueid"]
        )

    def test_post_configure(self):
        part_info = dict(
            HDF=[
                DatasetProducedInfo(
                    "det.data", "fn1", DatasetType.PRIMARY, 2, "/p/det", "/p/uid"
                ),
                DatasetProducedInfo(
                    "det.sum", "fn1", DatasetType.SECONDARY, 0, "/p/s1", "/p/uid"
                ),
                DatasetProducedInfo(
                    "det.min", "fn1", DatasetType.SECONDARY, 0, "/p/s2", "/p/uid"
                ),
            ]
        )
        self.o.on_post_configure(part_info)
        v = self.o.datasets.value
        assert v.name == ["det.data", "det.sum", "det.min"]
        assert v.filename == ["fn1", "fn1", "fn1"]
        assert v.type == [
            DatasetType.PRIMARY,
            DatasetType.SECONDARY,
            DatasetType.SECONDARY,
        ]
        assert list(v.rank) == [2, 0, 0]
        assert v.path == ["/p/det", "/p/s1", "/p/s2"]
        assert v.uniqueid == ["/p/uid", "/p/uid", "/p/uid"]
        self.o.on_reset()
        assert self.o.datasets.value.name == []
