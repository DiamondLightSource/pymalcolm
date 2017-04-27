import unittest
from mock import MagicMock, patch

from malcolm.gui.guimodel import GuiModel, BlockItem
from malcolm.core import Process, call_with_params
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
        self.controller = call_with_params(
            hello_block, self.process, mri="hello_block")
        self.process.start()
        self.m = GuiModel(self.process, self.controller.block_view())

    def tearDown(self):
        self.process.stop()

    def test_init(self):
        self.assertEqual(self.m.root_item.endpoint, ('hello_block',))
        self.assertEqual(len(self.m.root_item.children), 3)

    def test_find_item(self):
        m1, m2 = MagicMock(), MagicMock()
        BlockItem.items[("foo", "bar")] = m1
        BlockItem.items[("foo",)] = m2
        item, path = self.m.find_item(('foo', 'bar', 'bat'))
        self.assertEqual(item, m1)
        self.assertEqual(path, ['bat'])

    def test_update_root(self):
        b_item = self.m.root_item
        self.assertEqual([x.endpoint[-1] for x in b_item.children],
                         ["health", "error", "greet"])
        m_item = b_item.children[2]
        self.assertEqual(m_item.endpoint, ('hello_block', 'greet'))
        self.assertEqual(len(m_item.children), 2)
        n_item = m_item.children[0]
        self.assertEqual(n_item.endpoint,
                         ('hello_block', 'greet', 'takes', 'elements', 'name'))
        self.assertEqual(n_item.children, [])
        n_item = m_item.children[1]
        self.assertEqual(n_item.endpoint,
                         ('hello_block', 'greet', 'takes', 'elements', 'sleep'))
        self.assertEqual(n_item.children, [])
