import unittest
from mock import MagicMock, patch

from malcolm.gui.guimodel import GuiModel, BlockItem
from malcolm.core import Process
from malcolm.modules.demo.blocks import hello_block


class TestBlockModel(unittest.TestCase):
    @patch("malcolm.gui.guimodel.GuiModel.response_received")
    def setUp(self, mock_received):
        # Mock out the signal as it doesn't work without a QApplication running
        def register(func):
            self.saved_handle_response = func
        mock_received.connect.side_effect = register
        def emit(response):
            self.saved_handle_response(response)
        mock_received.emit.side_effect = emit

        self.process = Process("proc")
        self.controller = hello_block(mri="hello_block")[0]
        self.process.add_controller(self.controller)
        self.process.start()
        self.m = GuiModel(self.process, self.controller.make_view())

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_init(self):
        assert self.m.root_item.endpoint == ('hello_block',)
        assert len(self.m.root_item.children) == 3

    def test_find_item(self):
        m1, m2 = MagicMock(), MagicMock()
        BlockItem.items[("foo", "bar")] = m1
        BlockItem.items[("foo",)] = m2
        item, path = self.m.find_item(('foo', 'bar', 'bat'))
        assert item == m1
        assert path == ['bat']

    def test_update_root(self):
        b_item = self.m.root_item
        assert [x.endpoint[-1] for x in b_item.children] == (
                         ["health", "greet", "error"])
        m_item = b_item.children[1]
        assert m_item.endpoint == ('hello_block', 'greet')
        assert len(m_item.children) == 2
        n_item = m_item.children[0]
        assert n_item.endpoint == (
                         ('hello_block', 'greet', 'takes', 'elements', 'name'))
        assert n_item.children == []
        n_item = m_item.children[1]
        assert n_item.endpoint == (
                         ('hello_block', 'greet', 'takes', 'elements', 'sleep'))
        assert n_item.children == []
