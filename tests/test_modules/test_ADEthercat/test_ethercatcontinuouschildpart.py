from mock import MagicMock, Mock, call, patch

from malcolm.core import BadValueError, Put
from malcolm.modules.ADEthercat.parts import EthercatContinuousChildPart
from malcolm.modules.scanning.hooks import AbortHook, ConfigureHook, PreConfigureHook
from malcolm.modules.scanning.infos import DatasetType
from malcolm.testutil import ChildTestCase


class TestEthercatContinuousChildPart(ChildTestCase):
    def setUp(self):
        self.name = "ContinuousEthercat"
        self.mri = "CONTINUOUS-ETHERCAT"
        self.child_part = EthercatContinuousChildPart(self.name, self.mri)

    def test_constructor(self):
        self.assertEqual(self.name, self.child_part.name)
        self.assertEqual(self.mri, self.child_part.mri)
        self.assertEqual(False, self.child_part.faulty)

    @patch("malcolm.modules.builtin.parts.ChildPart.setup")
    def test_setup_hooks(self, super_setup_mock):
        registrar_mock = Mock(name="registrar_mock")
        self.child_part.setup(registrar_mock)

        super_setup_mock.assert_called_once_with(registrar_mock)
        registrar_mock.hook.assert_has_calls(
            [
                call(PreConfigureHook, self.child_part.reload),
                call(ConfigureHook, self.child_part.on_configure),
                call(AbortHook, self.child_part.on_abort),
            ]
        )

    @patch("malcolm.modules.builtin.parts.ChildPart.notify_dispatch_request")
    def test_notify_dispatch_request_with_design_Put_does_not_call(
        self, super_dispatch_request_mock
    ):
        mock_put_request = Mock(name="mock_put_request", spec=Put)
        mock_put_request.path = ["unused", "design"]

        self.child_part.notify_dispatch_request(mock_put_request)

        super_dispatch_request_mock.assert_not_called()

    @patch("malcolm.modules.builtin.parts.ChildPart.notify_dispatch_request")
    def test_notify_dispatch_request_with_other_Put_calls(
        self, super_dispatch_request_mock
    ):
        mock_put_request = Mock(name="mock_put_request", spec=Put)
        mock_put_request.path = ["unused", "other"]

        self.child_part.notify_dispatch_request(mock_put_request)

        super_dispatch_request_mock.assert_called_once_with(mock_put_request)

    @patch("malcolm.modules.builtin.parts.ChildPart.notify_dispatch_request")
    def test_notify_dispatch_request_with_other_request_with_design_path_calls(
        self, super_dispatch_request_mock
    ):
        mock_request = Mock(name="mock_request")
        mock_request.path = ["unused", "design"]

        self.child_part.notify_dispatch_request(mock_request)

        super_dispatch_request_mock.assert_called_once_with(mock_request)

    @patch("malcolm.modules.builtin.parts.ChildPart.notify_dispatch_request")
    def test_notify_dispatch_request_with_other_request_with_other_path_calls(
        self, super_dispatch_request_mock
    ):
        mock_request = Mock(name="mock_request")
        mock_request.path = ["unused", "other"]

        self.child_part.notify_dispatch_request(mock_request)

        super_dispatch_request_mock.assert_called_once_with(mock_request)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_init")
    def test_on_init_not_faulty_with_successful_on_init(self, super_on_init_mock):
        mock_context = Mock(name="mock_context")

        self.child_part.on_init(mock_context)

        super_on_init_mock.assert_called_once_with(mock_context)
        self.assertEqual(False, self.child_part.faulty)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_init")
    def test_on_init_faulty_with_BadValueError_Exception(self, super_on_init_mock):
        mock_context = Mock(name="mock_context")
        super_on_init_mock.side_effect = BadValueError

        self.child_part.on_init(mock_context)

        super_on_init_mock.assert_called_once_with(mock_context)
        self.assertEqual(True, self.child_part.faulty)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_init")
    def test_on_init_raises_for_other_Exception(self, super_on_init_mock):
        mock_context = Mock(name="mock_context")
        super_on_init_mock.side_effect = AssertionError

        self.assertRaises(AssertionError, self.child_part.on_init, mock_context)

        super_on_init_mock.assert_called_once_with(mock_context)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_reset")
    def test_on_reset_calls_when_not_faulty_and_abort_writeable(
        self, super_on_reset_mock
    ):
        mock_context = Mock(name="mock_context")
        mock_child = Mock(name="mock_child")
        mock_child.abort.meta.writeable = True
        mock_context.block_view.return_value = mock_child

        self.child_part.on_reset(mock_context)

        mock_child.abort.assert_called_once()
        super_on_reset_mock.assert_called_once_with(mock_context)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_reset")
    def test_on_reset_calls_when_not_faulty_and_abort_not_writeable(
        self, super_on_reset_mock
    ):
        mock_context = Mock(name="mock_context")
        mock_child = Mock(name="mock_child")
        mock_child.abort.meta.writeable = False
        mock_context.block_view.return_value = mock_child

        self.child_part.on_reset(mock_context)

        mock_child.abort.assert_not_called()
        super_on_reset_mock.assert_called_once_with(mock_context)

    @patch("malcolm.modules.builtin.parts.ChildPart.on_reset")
    def test_on_reset_does_not_call_when_faulty(self, super_on_reset_mock):
        mock_context = Mock(name="mock_context")
        mock_child = Mock(name="mock_child")
        mock_context.block_view.return_value = mock_child
        self.child_part.faulty = True

        self.child_part.on_reset(mock_context)

        mock_child.abort.assert_not_called()
        super_on_reset_mock.assert_not_called()

    def test_on_abort(self):
        mock_context = Mock(name="mock_context")
        mock_child = Mock(name="mock_child")
        mock_context.block_view.return_value = mock_child

        self.child_part.on_abort(mock_context)

        mock_child.abort.assert_called_once()

    def test_on_configure(self):
        mock_context = Mock(name="mock_context")
        mock_child = MagicMock(name="mock_child")
        mock_context.block_view.return_value = mock_child
        mock_generator = Mock(name="mock_generator")
        file_dir = "/this/is/a/file/dir"

        # Mock the rows in the dataset table
        name = "name"
        filename = "filename.h5"
        dataset_type = DatasetType.PRIMARY
        rank = 2
        path = "/entry/path"
        uniqueid = "unique_id"
        dataset_table_rows = [[name, filename, dataset_type, rank, path, uniqueid]]
        mock_child.datasets.value.rows.return_value = dataset_table_rows

        info_list = self.child_part.on_configure(mock_context, mock_generator, file_dir)

        mock_child.configure.assert_called_once_with(
            generator=mock_generator,
            fileDir=file_dir,
            formatName=self.name,
            fileTemplate="%s.h5",
        )
        self.assertEqual(1, len(info_list))
        self.assertEqual(name, info_list[0].name)
        self.assertEqual(filename, info_list[0].filename)
        self.assertEqual(dataset_type, info_list[0].type)
        self.assertEqual(rank, info_list[0].rank)
        self.assertEqual(path, info_list[0].path)
        self.assertEqual(uniqueid, info_list[0].uniqueid)
