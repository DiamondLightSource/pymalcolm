import sys
import unittest
from datetime import datetime

from mock import Mock, call, mock_open, patch
from ruamel.yaml import YAMLError
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import AbortedError, NotWriteableError, TimeoutError
from malcolm.modules.scanning.parts.scanrunnerpart import (
    RunnerStates,
    ScanOutcome,
    ScanRunnerPart,
)
from malcolm.modules.scanning.util import RunnableStates


class TestScanRunnerPart(unittest.TestCase):
    def setUp(self):
        self.name = "ScanRunner"
        self.mri = "ML-SCAN-RUNNER-01"
        self.single_scan_yaml = """
            - scan:
                name: coarse_2d
                repeats: 11
                generator:
                    generators:
                        - line:
                            axes: sample_y
                            units: mm
                            start: -0.3
                            stop: 0.5
                            size: 5
                            alternate: true
                        - line:
                            axes: sample_x
                            units: mm
                            start: 0.1
                            stop: 0.9
                            size: 5
                            alternate: true
                    duration: 0.002
                    continuous: true
                    delay_after: 0
            """

        self.two_scan_yaml = """
            - scan:
                name: coarse_2d
                repeats: 11
                generator:
                    generators:
                        - line:
                            axes: sample_y
                            units: mm
                            start: -0.3
                            stop: 0.5
                            size: 5
                            alternate: true
                        - line:
                            axes: sample_x
                            units: mm
                            start: 0.1
                            stop: 0.9
                            size: 5
                            alternate: true
                    duration: 0.002
                    continuous: true
                    delay_after: 0
            - scan:
                name: fine_2d_slow
                repeats: 3
                generator:
                    generators:
                        - line:
                            axes: sample_y
                            units: mm
                            start: 0.0
                            stop: 0.1
                            size: 5
                            alternate: true
                        - line:
                            axes: sample_x
                            units: mm
                            start: -0.3
                            stop: -0.34
                            size: 5
                            alternate: true
                    duration: 1.0
                    continuous: true
                    delay_after: 0
            """

        self.invalid_yaml = """
            features: [
              {
                name: lorem ipsum,
                bullets: [
                  "bullet 1",
                  "bullet 2"
                ]
              },{
                name: lorem ipsum 2,
                bullets: [
                ...
              }
            ]
            """

        self.unidentified_yaml = """
            - unidentified:
                name: coarse_2d
                repeats: 11
            """

    def test_new_instance_has_no_sets(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        self.assertEqual(None, scan_runner_part.runner_config)
        self.assertEqual({}, scan_runner_part.scan_sets)

    def test_get_kwargs_from_dict_returns_single_kwarg(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        input_dict = {"cat": 21, "dog": 15, "bird": 7}

        expected_dict = {"cat": 21}

        kwargs = scan_runner_part.get_kwargs_from_dict(input_dict, "cat")
        self.assertEqual(expected_dict, kwargs)

    def test_get_kwargs_from_dict_returns_two_kwargs(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        input_dict = {"cat": 21, "dog": 15, "bird": 7}

        expected_dict = {"dog": 15, "bird": 7}

        kwargs = scan_runner_part.get_kwargs_from_dict(input_dict, ["dog", "bird"])
        self.assertEqual(expected_dict, kwargs)

    def test_get_kwargs_from_dict_returns_empty_kwargs(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        input_dict = {"cat": 21, "dog": 15, "bird": 7}

        expected_dict = {}

        kwargs = scan_runner_part.get_kwargs_from_dict(input_dict, "moose")
        self.assertEqual(expected_dict, kwargs)

    def compare_compound_generator(self, expected_gen, actual_gen):
        self.assertEqual(expected_gen.duration, actual_gen.duration)
        self.assertEqual(expected_gen.continuous, actual_gen.continuous)
        self.assertEqual(expected_gen.delay_after, actual_gen.delay_after)

        for generator in range(len(actual_gen.generators)):
            self.compare_line_generator(
                expected_gen.generators[generator], actual_gen.generators[generator]
            )

    def compare_line_generator(self, expected_gen, actual_gen):
        self.assertEqual(expected_gen.axes, actual_gen.axes)
        self.assertEqual(expected_gen.units, actual_gen.units)
        self.assertEqual(expected_gen.start, actual_gen.start)
        self.assertEqual(expected_gen.stop, actual_gen.stop)
        self.assertEqual(expected_gen.size, actual_gen.size)
        self.assertEqual(expected_gen.alternate, actual_gen.alternate)

    def test_parse_compound_generator_parses_with_all_args(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        duration = 0.02
        continuous = False
        delay_after = 0.5

        line_x_axes = "sample_x"
        line_x_start = 0.1
        line_x_stop = 0.6
        line_x_size = 5
        line_x_alternate = False

        line_y_axes = "sample_y"
        line_y_start = -0.3
        line_y_stop = 0.4
        line_y_size = 10

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator_dict = {
            "duration": duration,
            "continuous": continuous,
            "delay_after": delay_after,
            "generators": [{"line": line_x}, {"line": line_y}],
        }

        expected_line_generators = [
            LineGenerator(
                line_x_axes,
                units,
                line_x_start,
                line_x_stop,
                line_x_size,
                alternate=line_x_alternate,
            ),
            LineGenerator(line_y_axes, units, line_y_start, line_y_stop, line_y_size),
        ]
        expected_compound_generator = CompoundGenerator(
            expected_line_generators,
            duration=duration,
            continuous=continuous,
            delay_after=delay_after,
        )

        compound_generator = scan_runner_part.parse_compound_generator(
            compound_generator_dict
        )

        self.compare_compound_generator(expected_compound_generator, compound_generator)

    def test_parse_compound_generator_parses_with_just_duration(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        duration = 1.4
        line_x_axes = "sample_x"
        line_x_start = 0.1
        line_x_stop = 0.6
        line_x_size = 5
        line_x_alternate = False

        line_y_axes = "sample_y"
        line_y_start = -0.3
        line_y_stop = 0.4
        line_y_size = 10

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator_dict = {
            "duration": duration,
            "generators": [{"line": line_x}, {"line": line_y}],
        }

        expected_line_generators = [
            LineGenerator(
                line_x_axes,
                units,
                line_x_start,
                line_x_stop,
                line_x_size,
                alternate=line_x_alternate,
            ),
            LineGenerator(line_y_axes, units, line_y_start, line_y_stop, line_y_size),
        ]
        expected_compound_generator = CompoundGenerator(
            expected_line_generators, duration=duration
        )

        compound_generator = scan_runner_part.parse_compound_generator(
            compound_generator_dict
        )

        self.compare_compound_generator(expected_compound_generator, compound_generator)

    def test_parse_compound_generator_raises_ValueError_without_duration(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        line_x_axes = "sample_x"
        line_x_start = 0.1
        line_x_stop = 0.6
        line_x_size = 5
        line_x_alternate = False

        line_y_axes = "sample_y"
        line_y_start = -0.3
        line_y_stop = 0.4
        line_y_size = 10

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator_dict = {"generators": [{"line": line_x}, {"line": line_y}]}

        self.assertRaises(
            ValueError,
            scan_runner_part.parse_compound_generator,
            compound_generator_dict,
        )

    def test_parse_compound_generator_raises_KeyError_without_generators(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        duration = 1.4

        compound_generator_dict = {
            "duration": duration,
        }

        self.assertRaises(
            KeyError, scan_runner_part.parse_compound_generator, compound_generator_dict
        )

    def test_parse_scan_parses_with_repeats(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        duration = 0.02
        continuous = False
        delay_after = 0.5
        repeats = 13
        name = "coarse_2D"

        line_x_axes = "sample_x"
        line_x_start = 1
        line_x_stop = 21
        line_x_size = 100
        line_x_alternate = False

        line_y_axes = "sample_y"
        line_y_start = -50
        line_y_stop = 51.2
        line_y_size = 99

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator = {
            "duration": duration,
            "continuous": continuous,
            "delay_after": delay_after,
            "generators": [{"line": line_x}, {"line": line_y}],
        }

        scan_dict = {"name": name, "repeats": repeats, "generator": compound_generator}

        expected_line_generators = [
            LineGenerator(
                line_x_axes,
                units,
                line_x_start,
                line_x_stop,
                line_x_size,
                alternate=line_x_alternate,
            ),
            LineGenerator(line_y_axes, units, line_y_start, line_y_stop, line_y_size),
        ]
        expected_compound_generator = CompoundGenerator(
            expected_line_generators,
            duration=duration,
            continuous=continuous,
            delay_after=delay_after,
        )

        scan_runner_part.parse_scan(scan_dict)

        scan = scan_runner_part.scan_sets[name]
        self.assertEqual(name, scan.name)
        self.assertEqual(repeats, scan.repeats)
        self.compare_compound_generator(expected_compound_generator, scan.generator)

    def test_parse_scan_parses_without_repeats(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        duration = 0.02
        continuous = False
        delay_after = 0.5
        name = "coarse_2D"

        line_x_axes = "sample_x"
        line_x_start = 1
        line_x_stop = 21
        line_x_size = 100
        line_x_alternate = False
        line_y_axes = "sample_y"
        line_y_start = -50
        line_y_stop = 51.2
        line_y_size = 99

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator = {
            "duration": duration,
            "continuous": continuous,
            "delay_after": delay_after,
            "generators": [{"line": line_x}, {"line": line_y}],
        }

        scan_dict = {"name": name, "generator": compound_generator}

        expected_line_generators = [
            LineGenerator(
                line_x_axes,
                units,
                line_x_start,
                line_x_stop,
                line_x_size,
                alternate=line_x_alternate,
            ),
            LineGenerator(line_y_axes, units, line_y_start, line_y_stop, line_y_size),
        ]
        expected_compound_generator = CompoundGenerator(
            expected_line_generators,
            duration=duration,
            continuous=continuous,
            delay_after=delay_after,
        )

        scan_runner_part.parse_scan(scan_dict)

        scan = scan_runner_part.scan_sets[name]
        self.assertEqual(name, scan.name)
        self.assertEqual(1, scan.repeats)
        self.compare_compound_generator(expected_compound_generator, scan.generator)

    def test_parse_scan_raises_KeyError_for_no_name(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        duration = 0.02
        continuous = False
        delay_after = 0.5

        line_x_axes = "sample_x"
        line_x_start = 1
        line_x_stop = 21
        line_x_size = 100
        line_x_alternate = False

        line_y_axes = "sample_y"
        line_y_start = -50
        line_y_stop = 51.2
        line_y_size = 99

        units = "mm"

        line_x = {
            "axes": line_x_axes,
            "units": units,
            "start": line_x_start,
            "stop": line_x_stop,
            "size": line_x_size,
            "alternate": line_x_alternate,
        }
        line_y = {
            "axes": line_y_axes,
            "units": units,
            "start": line_y_start,
            "stop": line_y_stop,
            "size": line_y_size,
        }

        compound_generator = {
            "duration": duration,
            "continuous": continuous,
            "delay_after": delay_after,
            "generators": [{"line": line_x}, {"line": line_y}],
        }

        scan_dict = {"generator": compound_generator}

        self.assertRaises(KeyError, scan_runner_part.parse_scan, scan_dict)

    def test_parse_scan_raises_KeyError_for_no_generator(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        name = "Fine_2D"

        scan_dict = {"name": name}

        self.assertRaises(KeyError, scan_runner_part.parse_scan, scan_dict)

    def test_loadFile_parses_for_single_scan(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.single_scan_yaml

        # Call loadFile to parse our mocked string
        scan_runner_part.loadFile()

        # Check that we have loaded the scan
        scan_name = "coarse_2d"
        scan = scan_runner_part.scan_sets[scan_name]
        self.assertEqual(scan_name, scan.name)
        self.assertEqual(11, scan.repeats)

        # Check that we are configured
        self.assertEqual(11, scan_runner_part.scans_configured.value)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.CONFIGURED),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual("Load complete", scan_runner_part.runner_status_message.value)

    def test_loadFile_parses_for_two_scans(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.two_scan_yaml

        # Call loadFile to parse our mocked string
        scan_runner_part.loadFile()

        # Check that we have loaded the scans
        coarse_scan_name = "coarse_2d"
        scan = scan_runner_part.scan_sets[coarse_scan_name]
        self.assertEqual(coarse_scan_name, scan.name)
        self.assertEqual(11, scan.repeats)

        fine_scan_name = "fine_2d_slow"
        scan = scan_runner_part.scan_sets[fine_scan_name]
        self.assertEqual(fine_scan_name, scan.name)
        self.assertEqual(3, scan.repeats)

        # Check that we are configured
        self.assertEqual(14, scan_runner_part.scans_configured.value)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.CONFIGURED),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual("Load complete", scan_runner_part.runner_status_message.value)

    @patch("__main__.open")
    def test_loadFile_throws_IOError_for_bad_filepath(self, mock_open):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file opener
        mock_open.side_effect = IOError("Fake IOError")

        # Call loadFile which should throw our IOError
        self.assertRaises(IOError, scan_runner_part.loadFile)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.FAULT),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual(
            "Could not read scan file", scan_runner_part.runner_status_message.value
        )

    def test_loadFile_throws_YAMLError_for_invalid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.invalid_yaml

        # Call loadFile to parse our mocked string
        self.assertRaises(YAMLError, scan_runner_part.loadFile)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.FAULT),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual(
            "Could not parse scan file", scan_runner_part.runner_status_message.value
        )

    def test_loadFile_throws_ValueError_for_unknown_key_in_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.unidentified_yaml

        # Call loadFile to parse our mocked string
        self.assertRaises(ValueError, scan_runner_part.loadFile)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.FAULT),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual(
            "Unidentified key in YAML", scan_runner_part.runner_status_message.value
        )

    def test_parse_yaml_parses_valid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.parse_yaml(self.single_scan_yaml)

    def test_parse_yaml_throws_YAMLError_for_invalid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        self.assertRaises(YAMLError, scan_runner_part.parse_yaml, self.invalid_yaml)
        self.assertEqual(
            ScanRunnerPart.get_enum_label(RunnerStates.FAULT),
            scan_runner_part.runner_state.value,
        )
        self.assertEqual(
            "Could not parse scan file", scan_runner_part.runner_status_message.value
        )

    def test_get_enum_label_capitalises_state(self):
        expected_label = "Configured"

        self.assertEqual(
            expected_label, ScanRunnerPart.get_enum_label(RunnerStates.CONFIGURED)
        )

    def test_increment_scan_successes(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        self.assertEqual(0, scan_runner_part.scan_successes.value)
        self.assertEqual(0, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scan_successes()
        self.assertEqual(1, scan_runner_part.scan_successes.value)
        self.assertEqual(1, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scan_successes()
        self.assertEqual(2, scan_runner_part.scan_successes.value)
        self.assertEqual(2, scan_runner_part.scans_completed.value)

    def test_increment_scan_failures(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        self.assertEqual(0, scan_runner_part.scan_failures.value)
        self.assertEqual(0, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scan_failures()
        self.assertEqual(1, scan_runner_part.scan_failures.value)
        self.assertEqual(1, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scan_failures()
        self.assertEqual(2, scan_runner_part.scan_failures.value)
        self.assertEqual(2, scan_runner_part.scans_completed.value)

    def test_increment_scans_completed(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        self.assertEqual(0, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scans_completed()
        self.assertEqual(1, scan_runner_part.scans_completed.value)

        scan_runner_part.increment_scans_completed()
        self.assertEqual(2, scan_runner_part.scans_completed.value)

    def test_run_raises_ValueError_for_no_loaded_scan_set(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        runner_status_message_mock = Mock(name="runner_status_message_mock")
        scan_runner_part.runner_status_message = runner_status_message_mock

        self.assertRaises(ValueError, scan_runner_part.run, Mock())
        runner_status_message_mock.set_value.assert_called_once_with(
            "No scan file loaded"
        )

    def test_run_completes_when_single_scan_set_is_loaded(self):
        # Create some mock objects
        context_mock = Mock(name="context_mock")
        scan_block_mock = Mock(name="mock_scan_block")
        context_mock.block_view.return_value = scan_block_mock

        # Setup the part with a valid scan set
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.setup(context_mock)
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.single_scan_yaml
        scan_runner_part.loadFile()

        # Mock the create_and_get_sub_directory and run_scan_set methods
        sub_directory = "/test/sub/directory"

        create_and_get_sub_directory_mock = Mock(
            name="create_and_get_sub_directory_mock"
        )
        scan_runner_part.create_and_get_sub_directory = (
            create_and_get_sub_directory_mock
        )
        scan_runner_part.create_and_get_sub_directory.return_value = sub_directory

        run_scan_set_mock = Mock(name="run_scan_set_mock")
        scan_runner_part.run_scan_set = run_scan_set_mock

        # Mock the output directory path
        root_directory = "/test/scan/directory"
        scan_runner_part.output_directory = Mock()
        scan_runner_part.output_directory.value = root_directory

        # Call our run method
        scan_runner_part.run(context_mock)

        # Check method calls
        calls = []
        for key in scan_runner_part.scan_sets:
            calls.append(
                call(
                    scan_runner_part.scan_sets[key],
                    scan_block_mock,
                    sub_directory,
                    sub_directory + "/report.txt",
                )
            )
        run_scan_set_mock.assert_has_calls(calls)

    def test_run_completes_when_two_scan_sets_are_loaded(self):
        # Create some mock objects
        context_mock = Mock(name="context_mock")
        scan_block_mock = Mock(name="mock_scan_block")
        context_mock.block_view.return_value = scan_block_mock

        # Setup the part with a valid scan set
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.setup(context_mock)
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.two_scan_yaml
        scan_runner_part.loadFile()

        # Mock the create_and_get_sub_directory and run_scan_set methods
        sub_directory = "/test/sub/directory"

        create_and_get_sub_directory_mock = Mock(
            name="create_and_get_sub_directory_mock"
        )
        scan_runner_part.create_and_get_sub_directory = (
            create_and_get_sub_directory_mock
        )
        scan_runner_part.create_and_get_sub_directory.return_value = sub_directory

        run_scan_set_mock = Mock(name="run_scan_set_mock")
        scan_runner_part.run_scan_set = run_scan_set_mock

        # Mock the output directory path
        root_directory = "/test/scan/directory"
        scan_runner_part.output_directory = Mock()
        scan_runner_part.output_directory.value = root_directory

        # Call our run method
        scan_runner_part.run(context_mock)

        # Check method calls
        calls = []
        for key in scan_runner_part.scan_sets:
            calls.append(
                call(
                    scan_runner_part.scan_sets[key],
                    scan_block_mock,
                    sub_directory,
                    sub_directory + "/report.txt",
                )
            )
        run_scan_set_mock.assert_has_calls(calls)

    def test_run_scan_set(self):
        # Setup the part with a valid scan set
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.setup(Mock())
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.single_scan_yaml
        scan_runner_part.loadFile()

        # Mock scan block
        scan_block_mock = Mock(name="scan_block_mock")

        # Mock the scan_set and its get_compound_generator method
        scan_set_mock = Mock(name="scan_set_mock")
        generator_mock = Mock(name="generator")
        scan_set_mock.generator = generator_mock

        # Set the mock scan set attributes to match real scan set
        scan_set_name = "coarse_2d"
        real_scan_set = scan_runner_part.scan_sets[scan_set_name]
        scan_set_mock.repeats = real_scan_set.repeats
        scan_set_mock.name = scan_set_name

        # Mock the run scan method
        run_scan_mock = Mock(name="run_scan_mock")
        scan_runner_part.run_scan = run_scan_mock

        # Mock the create_and_get_set_directory method
        set_directory = "/test/set/directory"
        create_and_set_directory_mock = Mock(
            name="mock_create_and_get_set_directory_method"
        )
        scan_runner_part.create_and_get_set_directory = create_and_set_directory_mock
        scan_runner_part.create_and_get_set_directory.return_value = set_directory

        # Call the run_scan_set method
        sub_directory = "/test/sub/directory"
        report_filepath = sub_directory + "/report.txt"
        scan_runner_part.run_scan_set(
            scan_set_mock, scan_block_mock, sub_directory, report_filepath
        )

        # Check the create_and_get_set_directory_method was called
        create_and_set_directory_mock.assert_called_once_with(
            sub_directory, scan_set_name
        )

        # Check that our mock run_scan method was called the correct number of times
        self.assertEqual(scan_set_mock.repeats, run_scan_mock.call_count)
        calls = []
        for scan_number in range(1, scan_set_mock.repeats + 1):
            calls.append(
                call(
                    scan_set_name,
                    scan_block_mock,
                    set_directory,
                    scan_number,
                    report_filepath,
                    generator_mock,
                )
            )
        run_scan_mock.assert_has_calls(calls)

    def test_abort_calls_context_abort(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.context = Mock(name="context_mock")
        scan_runner_part.set_runner_state = Mock(name="set_runner_state_mock")
        scan_runner_part.runner_status_message = Mock(name="runner_status_message_mock")

        # Call abort
        passed_context_mock = Mock(name="passed_context_mock")
        scan_block_mock = Mock(name="scan_block_mock")
        passed_context_mock.block_view.return_value = scan_block_mock
        scan_runner_part.abort(passed_context_mock)

        # Check the resulting calls
        scan_runner_part.context.stop.assert_called_once()
        scan_runner_part.set_runner_state.assert_called_once_with(RunnerStates.ABORTED)
        passed_context_mock.block_view.assert_called_once_with(self.mri)
        scan_block_mock.abort.assert_called_once()
        scan_runner_part.runner_status_message.set_value.assert_called_once_with(
            "Aborted scans"
        )

    def test_abort_with_no_context_does_not_raise_Error(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.set_runner_state = Mock(name="set_runner_state_mock")
        scan_runner_part.runner_status_message = Mock(name="runner_status_message_mock")

        # Call abort
        scan_runner_part.abort(Mock(name="passed_context_mock"))

    @patch("malcolm.modules.scanning.parts.scanrunnerpart.datetime")
    def test_get_current_datetime(self, datetime_mock):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # Mock the datetime.now() method
        datetime_mock.now.return_value = datetime(2019, 7, 24, 13, 30, 59)

        expected_string = "2019-07-24-13:30:59"
        actual_string = scan_runner_part.get_current_datetime()

        self.assertEqual(expected_string, actual_string)

    @patch("malcolm.modules.scanning.parts.scanrunnerpart.datetime")
    def test_get_current_datetime_with_separator(self, datetime_mock):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # Mock the datetime.now() method
        datetime_mock.now.return_value = datetime(2019, 7, 24, 13, 30, 59)

        expected_string = "2019-07-24-13.30.59"
        actual_string = scan_runner_part.get_current_datetime(time_separator=".")

        self.assertEqual(expected_string, actual_string)

    def test_scan_is_aborting_is_True_for_ABORTING_state(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        scan_block_mock = Mock(name="scan_block_mock")
        scan_block_mock.state.value = RunnableStates.ABORTING

        self.assertEqual(True, scan_runner_part.scan_is_aborting(scan_block_mock))

    def test_scan_is_aborting_is_False_for_other_state(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        scan_block_mock = Mock(name="scan_block_mock")
        scan_block_mock.state.value = RunnableStates.FAULT

        self.assertEqual(False, scan_runner_part.scan_is_aborting(scan_block_mock))

    def test_get_file_contents_returns_for_success(
        self,
    ):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Mock the scan file
        scan_file_mock = Mock(name="scan_file_mock")
        scan_file_mock.value.return_value = "file_string"
        scan_runner_part.scan_file = scan_file_mock

        # Mock open
        expected_string = "test_file_string"
        mocked_open = mock_open(read_data=expected_string)

        if sys.version_info[0] < 3:
            with patch("__builtin__.open", mocked_open):
                actual_string = scan_runner_part.get_file_contents()
        else:
            with patch("builtins.open", mocked_open):
                actual_string = scan_runner_part.get_file_contents()

        self.assertEqual(expected_string, actual_string)

    def test_get_report_string(self):
        set_name = "set-name"
        scan_number = 12
        outcome = ScanOutcome.SUCCESS
        start_time = "2020-01-06-15:54:17"
        end_time = "2020-01-06-16:04:10"
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        expected_string = "{set:<30}{no:<10}{outcome:<14}{start:<20}{end}".format(
            set=set_name,
            no=scan_number,
            outcome=scan_runner_part.get_enum_label(outcome),
            start=start_time,
            end=end_time,
        )
        actual_string = scan_runner_part.get_report_string(
            set_name, scan_number, outcome, start_time, end_time
        )

        self.assertEqual(expected_string, actual_string)

    def test_add_report_line_writes_line(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        report_string = "example_report_string"
        report_filepath = "/report/filepath/report.txt"

        # Mock open
        mocked_open = mock_open()

        if sys.version_info[0] < 3:
            with patch("__builtin__.open", mocked_open):
                scan_runner_part.add_report_line(report_filepath, report_string)
        else:
            with patch("builtins.open", mocked_open):
                scan_runner_part.add_report_line(report_filepath, report_string)

        mocked_open.assert_called_once_with(report_filepath, "a+")
        file_handle = mocked_open()
        file_handle.write.assert_called_once_with(report_string + "\n")

    def test_add_report_line_throws_IO_Error(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        report_string = "example_report_string"
        report_filepath = "/report/filepath/report.txt"

        # Mock runner state and status
        scan_runner_part.set_runner_state = Mock(name="runner_state_mock")
        scan_runner_part.runner_status_message = Mock(name="status_message_mock")

        # Mock open
        mocked_open = mock_open()
        mocked_open.side_effect = IOError

        if sys.version_info[0] < 3:
            with patch("__builtin__.open", mocked_open):
                self.assertRaises(
                    IOError,
                    scan_runner_part.add_report_line,
                    report_filepath,
                    report_string,
                )
        else:
            with patch("builtins.open", mocked_open):
                self.assertRaises(
                    IOError,
                    scan_runner_part.add_report_line,
                    report_filepath,
                    report_string,
                )

        scan_runner_part.set_runner_state.assert_called_once_with(RunnerStates.FAULT)
        scan_runner_part.runner_status_message.set_value.assert_called_once_with(
            "Error writing report file"
        )

    def test_get_root_directory_gets_directory(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Mock the output directory
        expected_root_directory = "expected/root/directory"
        mock_output_directory = Mock(name="output_directory_mock")
        mock_output_directory.value = expected_root_directory
        scan_runner_part.output_directory = mock_output_directory

        actual_root_directory = scan_runner_part.get_root_directory()

        self.assertEqual(expected_root_directory, actual_root_directory)

    def test_get_root_directory_removes_trailing_slash(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Mock the output directory
        expected_root_directory = "expected/root/directory"
        mock_output_directory = Mock(name="output_directory_mock")
        mock_output_directory.value = expected_root_directory + "/"
        scan_runner_part.output_directory = mock_output_directory

        actual_root_directory = scan_runner_part.get_root_directory()

        self.assertEqual(expected_root_directory, actual_root_directory)


class TestScanRunnerPartCreateDirectoryMethods(unittest.TestCase):
    def setUp(self):
        name = "ScanRunner"
        self.mri = "ML-SCAN-RUNNER-01"
        self.scan_runner_part = ScanRunnerPart(name, self.mri)

    def mock_datetime(self, mock_date):
        mock_datetime = Mock(name="get_current_datetime_mock")
        mock_datetime.return_value = mock_date
        self.scan_runner_part.get_current_datetime = mock_datetime

    def mock_create_directory(self):
        create_directory_mock = Mock(name="create_directory_mock")
        self.scan_runner_part.create_directory = create_directory_mock

    @patch("os.mkdir")
    def test_create_directory(self, mock_mkdir):
        test_directory = "test/directory"

        self.scan_runner_part.create_directory(test_directory)

        mock_mkdir.assert_called_once_with(test_directory)

    @patch("os.mkdir")
    def test_create_directory_throws_IOError_for_mkdir_OSError(self, mock_mkdir):
        self.scan_runner_part.runner_status_message = Mock(name="runner_status_mock")
        self.scan_runner_part.set_runner_state = Mock(name="set_runner_state_mock")
        test_directory = "test/directory"
        mock_mkdir.side_effect = OSError

        self.assertRaises(
            IOError, self.scan_runner_part.create_directory, test_directory
        )
        self.scan_runner_part.set_runner_state.assert_called_once_with(
            RunnerStates.FAULT
        )
        self.scan_runner_part.runner_status_message.set_value.assert_called_once_with(
            "Could not create directory"
        )

    def test_create_and_get_sub_directory_returns_sub_directory(self):
        root_directory = "root/directory"
        mock_date = "2019-08-24-11-32-53"
        expected_sub_directory = root_directory + "/" + self.mri + "-" + mock_date

        # Set up mocks
        self.mock_datetime(mock_date)
        self.mock_create_directory()

        actual_sub_directory = self.scan_runner_part.create_and_get_sub_directory(
            root_directory
        )

        self.assertEqual(expected_sub_directory, actual_sub_directory)
        self.scan_runner_part.create_directory.assert_called_once_with(
            expected_sub_directory
        )

    def test_create_and_get_set_directory_returns_set_directory(self):
        sub_directory = "root/sub/directory"
        set_name = "example-set-name"
        expected_set_directory = sub_directory + "/scanset-" + set_name

        # Set up mocks
        self.mock_create_directory()

        actual_set_directory = self.scan_runner_part.create_and_get_set_directory(
            sub_directory, set_name
        )

        self.assertEqual(expected_set_directory, actual_set_directory)
        self.scan_runner_part.create_directory.assert_called_once_with(
            expected_set_directory
        )

    def test_create_and_get_scan_directory_returns_scan_directory(self):
        set_directory = "root/set/directory"
        scan_number = 193
        expected_scan_directory = set_directory + "/scan-" + str(scan_number)

        # Set up mocks
        self.mock_create_directory()

        actual_scan_directory = self.scan_runner_part.create_and_get_scan_directory(
            set_directory, scan_number
        )

        self.assertEqual(expected_scan_directory, actual_scan_directory)
        self.scan_runner_part.create_directory.assert_called_once_with(
            expected_scan_directory
        )


class TestScanRunnerPartRunScanMethod(unittest.TestCase):
    def setUp(self):
        name = "ScanRunner"
        mri = "ML-SCAN-RUNNER-01"

        single_scan_yaml = """
            - scan:
                name: coarse_2d
                repeats: 11
                generator:
                    generators:
                        - line:
                            axes: sample_y
                            units: mm
                            start: -0.3
                            stop: 0.5
                            size: 5
                            alternate: true
                        - line:
                            axes: sample_x
                            units: mm
                            start: 0.1
                            stop: 0.9
                            size: 5
                            alternate: true
                    duration: 0.002
                    continuous: true
                    delay_after: 0
            """

        self.scan_runner_part = ScanRunnerPart(name, mri)
        self.scan_runner_part.setup(Mock())
        self.scan_runner_part.get_file_contents = Mock()
        self.scan_runner_part.get_file_contents.return_value = single_scan_yaml
        self.scan_runner_part.loadFile()

        # Mock the create_and_get_scan_directory method
        self.scan_directory = "/test/scan/directory"
        self.create_and_get_scan_directory_mock = Mock(
            name="create_and_get_scan_directory_mock"
        )
        self.create_and_get_scan_directory_mock.return_value = self.scan_directory
        self.scan_runner_part.create_and_get_scan_directory = (
            self.create_and_get_scan_directory_mock
        )

        # Mock generator
        self.generator_mock = Mock(name="generator_mock")

        # Mock scan block, set state to READY
        self.scan_block_mock = Mock(name="scan_block_mock")
        self.scan_block_mock.state.value = RunnableStates.READY

        # Mock get_current_datetime method
        self.start_time = "2019-02-24-21:19:54"
        get_current_datetime_mock = Mock(name="get_current_datetime_mock")
        get_current_datetime_mock.return_value = self.start_time
        self.scan_runner_part.get_current_datetime = get_current_datetime_mock

        # Mock the add_report_line method
        self.add_report_line_mock = Mock(name="add_report_line_mock")
        self.scan_runner_part.add_report_line = self.add_report_line_mock

        # Mock the increment_scan_successes method
        self.increment_scan_successes_mock = Mock(name="increment_scan_successes_mock")
        self.scan_runner_part.increment_scan_successes = (
            self.increment_scan_successes_mock
        )

        # Mock the increment_scan_failures method
        self.increment_scan_failures_mock = Mock(name="increment_scan_failures_mock")
        self.scan_runner_part.increment_scan_failures = (
            self.increment_scan_failures_mock
        )

        # Mock the logger
        self.logger_mock = Mock(name="logger_mock")
        self.scan_runner_part.log = self.logger_mock

        # run_scan args
        self.set_directory = "/test/set/directory"
        self.set_name = "10um_fine"
        self.scan_number = 21
        self.report_filepath = "/test/sub/directory/report.txt"

    def get_expected_report_string(self, scan_outcome):
        report_string = self.scan_runner_part.get_report_string(
            self.set_name,
            self.scan_number,
            scan_outcome,
            self.start_time,
            self.start_time,
        )

        return report_string

    def test_run_scan_succeeds_for_scan_success(self):
        # Our mocked scan block will return nicely for a success
        self.scan_block_mock.run.return_value = None

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.SUCCESS)
        )

        # Check the outcome calls
        self.increment_scan_successes_mock.assert_called_once()

    def test_run_scan_is_misconfigured_when_scan_block_configure_throws_AssertionError(
        self,
    ):
        # Our mocked scan block will throw an AssertionError
        self.scan_block_mock.configure.side_effect = AssertionError()

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath,
            self.get_expected_report_string(ScanOutcome.MISCONFIGURED),
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_is_misconfigured_when_scan_block_configure_throws_other_exception(
        self,
    ):
        # Our mocked scan block will throw an exception
        self.scan_block_mock.configure.side_effect = ValueError("Invalid value")

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath,
            self.get_expected_report_string(ScanOutcome.MISCONFIGURED),
        )

        # Check that we logged the unidentified exception
        self.logger_mock.error.assert_called_once_with(
            "Unhandled exception for scan {no} in {set}: ({type_e}) {e}".format(
                type_e=ValueError, no=21, set=self.set_name, e="Invalid value"
            )
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_fails_for_scan_TimeoutError(self):
        # Our mocked scan block will raise a TimeoutError when called
        self.scan_block_mock.run.side_effect = TimeoutError()

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.TIMEOUT)
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_fails_for_scan_NotWriteableError(self):
        # Our mocked scan block will raise a NotWriteableError when called
        self.scan_block_mock.run.side_effect = NotWriteableError()

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath,
            self.get_expected_report_string(ScanOutcome.NOTWRITEABLE),
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_fails_for_scan_AbortedError(self):
        # Our mocked scan block will raise an AbortedError when called
        self.scan_block_mock.run.side_effect = AbortedError()

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.ABORTED)
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_fails_for_scan_AssertionError(self):
        # Our mocked scan block will raise a NotWriteableError when called
        self.scan_block_mock.run.side_effect = AssertionError()

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.FAIL)
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_fails_for_scan_OtherError(self):
        # Our mocked scan block will raise a generic exception
        exception_text = "Unidentified exception"
        self.scan_block_mock.run.side_effect = Exception(exception_text)

        # We also need to mock the logger to check it logs the exception
        logger_mock = Mock(name="logger_mock")
        self.scan_runner_part.log = logger_mock

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check that we logged the unidentified exception
        logger_mock.error.assert_called_once_with(
            "Unhandled exception for scan {no} in {set}: ({type_e}) {e}".format(
                type_e=Exception,
                no=self.scan_number,
                set=self.set_name,
                e=exception_text,
            )
        )

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.OTHER)
        )

        # Check the outcome calls
        self.increment_scan_failures_mock.assert_called_once()

    def test_run_scan_sleeps_if_scan_block_is_ABORTING(self):
        # Our mocked scan block will return nicely for a success
        self.scan_block_mock.run.return_value = None

        # Mock our context
        context_mock = Mock(name="context_mock")
        self.scan_runner_part.context = context_mock

        # Mock the scan_is_aborting method
        is_aborting_mock = Mock(name="is_aborting_mock")
        is_aborting_mock.side_effect = [True, False]
        self.scan_runner_part.scan_is_aborting = is_aborting_mock

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check we slept
        context_mock.sleep.assert_called_once_with(0.1)

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, self.get_expected_report_string(ScanOutcome.SUCCESS)
        )

        # Check the outcome calls
        self.increment_scan_successes_mock.assert_called_once()

    def test_run_scan_calls_reset_if_scan_block_is_not_READY(self):
        # Our mocked scan block will return nicely for a success
        self.scan_block_mock.run.return_value = None

        # Mock reset method and set state
        self.scan_block_mock.state.value = RunnableStates.ABORTED

        # Mock the report string method
        mock_report_string = Mock(name="report_string_mock")
        report_string = "report_string"
        mock_report_string.return_value = report_string
        self.scan_runner_part.get_report_string = mock_report_string

        # Mock context
        self.scan_runner_part.context = Mock(name="context_mock")

        # Call the run_scan method
        self.scan_runner_part.run_scan(
            self.set_name,
            self.scan_block_mock,
            self.set_directory,
            self.scan_number,
            self.report_filepath,
            self.generator_mock,
        )

        # Check reset was called
        self.scan_block_mock.reset.assert_called_once()

        # Check the standard method calls
        self.create_and_get_scan_directory_mock.assert_called_once_with(
            self.set_directory, self.scan_number
        )
        self.scan_block_mock.configure.assert_called_once_with(
            self.generator_mock, fileDir=self.scan_directory
        )
        self.scan_block_mock.run.assert_called_once()

        # Check the reporting was called
        self.add_report_line_mock.assert_called_once_with(
            self.report_filepath, report_string
        )

        # Check the outcome calls
        self.increment_scan_successes_mock.assert_called_once()
