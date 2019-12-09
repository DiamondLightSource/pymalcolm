import unittest
from mock import Mock, patch

from ruamel.yaml import YAMLError
from malcolm.modules.scanning.parts.scanrunnerpart import ScanDimension, \
    Axes, ScanSet, ScanRunnerPart, RunnerStates


# TODO: tests for run, run_scan_set and run_scan
# TODO: tests for get report string


class TestScanDimension(unittest.TestCase):

    def test_attributes_are_initialised(self):
        start = 0.0
        stop = 10.0
        steps = 10

        scan_dimension = ScanDimension(start, stop, steps)

        self.assertEqual(start, scan_dimension.start)
        self.assertEqual(stop, scan_dimension.stop)
        self.assertEqual(steps, scan_dimension.steps)


class TestAxes(unittest.TestCase):

    def test_attributes_are_initialised(self):
        name = "Fine_XY"
        fast_axis = "x"
        slow_axis = "y"
        units = "mm"

        axes = Axes(name, fast_axis, slow_axis, units)

        self.assertEqual(name, axes.name)
        self.assertEqual(fast_axis, axes.fast_axis)
        self.assertEqual(slow_axis, axes.slow_axis)
        self.assertEqual(units, axes.units)


class TestScanSet(unittest.TestCase):

    def setUp(self):
        self.name = "fine_scan_1um_step"
        self.axes = Axes("Fine_XY", "x", "y", "mm")
        self.fast_dimension = ScanDimension(0.0, 5.0, 6)
        self.slow_dimension = ScanDimension(0.0, 10.0, 11)
        self.duration = 0.01
        self.alternate = True
        self.continuous = False
        self.repeats = 17

    def test_attributes_are_initialised(self):
        scan_set = ScanSet(self.name, self.axes, self.fast_dimension,
                           self.slow_dimension, self.duration,
                           self.alternate, self.continuous, self.repeats)

        self.assertEqual(self.name, scan_set.name)
        self.assertEqual(self.axes, scan_set.axes)
        self.assertEqual(self.fast_dimension, scan_set.fast_dimension)
        self.assertEqual(self.slow_dimension, scan_set.slow_dimension)
        self.assertEqual(self.duration, scan_set.duration)
        self.assertEqual(self.alternate, scan_set.alternate)
        self.assertEqual(self.continuous, scan_set.continuous)
        self.assertEqual(self.repeats, scan_set.repeats)

    def test_get_compound_generator(self):
        scan_set = ScanSet(self.name, self.axes, self.fast_dimension,
                           self.slow_dimension, self.duration,
                           self.alternate, self.continuous, self.repeats)

        generator = scan_set.get_compound_generator()

        self.assertEqual("mm", generator.units['x'])
        self.assertEqual("mm", generator.units['y'])
        self.assertEqual(self.duration, generator.duration)
        self.assertEqual(self.continuous, generator.continuous)
        self.assertEqual(['y', 'x'], generator.axes)


class TestScanRunnerPart(unittest.TestCase):

    def setUp(self):
        self.name = "ScanRunner"
        self.mri = "ML-SCAN-RUNNER-01"

        self.good_yaml = \
            """
            - axes:
                name: xy_stages
                fast_axis: j08_x
                slow_axis: j08_y
                units: mm
            
            - axes:
                name: xz_stages
                fast_axis: j08_x
                slow_axis: j08_z
                units: mm
            
            - ScanSet2d:
                name: fine_70um_10um_step
                axes: xy_stages
                start_fast: -0.035
                stop_fast: 0.8
                steps_fast: 25
                start_slow: -0.5
                stop_slow: 0.5
                steps_slow: 8
                alternate: True
                continuous: False
                repeats: 1
                duration: 0.1
            """

        self.invalid_yaml = \
            """
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

    def test_new_instance_has_no_sets(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        self.assertEqual(None, scan_runner_part.runner_config)
        self.assertEqual({}, scan_runner_part.axes_sets)
        self.assertEqual({}, scan_runner_part.scan_sets)

    @staticmethod
    def compare_axes(axes_a, axes_b):
        if axes_a.name == axes_b.name and axes_a.units == axes_b.units \
                and axes_a.fast_axis == axes_b.fast_axis \
                and axes_a.slow_axis == axes_b.slow_axis:
            return True
        else:
            return False

    @staticmethod
    def compare_dimensions(dimension_a, dimension_b):
        if dimension_a.start == dimension_b.start \
                and dimension_a.stop == dimension_b.stop \
                and dimension_a.steps == dimension_b.steps:
            return True
        else:
            return False

    def compare_scan_set(self, set_a, set_b):
        if set_a.name == set_b.name and set_a.duration == set_b.duration \
                and set_a.alternate == set_b.alternate \
                and set_a.continuous == set_b.continuous \
                and set_a.repeats == set_b.repeats:
            if self.compare_axes(set_a.axes, set_b.axes) is not True:
                self.fail("Axes do not match")
            if self.compare_dimensions(set_a.fast_dimension, set_b.fast_dimension) is not True:
                self.fail("Fast dimensions do not match: {0}, {1}".format(set_a.fast_dimension, set_b.fast_dimension))
            if self.compare_dimensions(set_a.slow_dimension, set_b.slow_dimension) is not True:
                self.fail("Slow dimensions do not match: {0}, {1}".format(set_a.slow_dimension, set_b.slow_dimension))
            return True
        else:
            return False

    def test_loadFile(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.good_yaml

        # Call loadFile to parse our mocked string
        scan_runner_part.loadFile()

        # Check the loaded axes

        # Expected axes in our set
        expected_axes_xy = Axes("xy_stages", "j08_x", "j08_y", "mm")
        expected_axes_xz = Axes("xz_stages", "j08_x", "j08_z", "mm")

        # Actual axes
        actual_axes_xy = scan_runner_part.axes_sets['xy_stages']
        actual_axes_xz = scan_runner_part.axes_sets['xz_stages']

        self.assertEqual(2, len(scan_runner_part.axes_sets))
        self.assertTrue(self.compare_axes(expected_axes_xy, actual_axes_xy))
        self.assertTrue(self.compare_axes(expected_axes_xz, actual_axes_xz))

        # Check the loaded scan sets

        # Expected scan set
        fast_dimension = ScanDimension(-0.035, 0.8, 25)
        slow_dimension = ScanDimension(-0.5, 0.5, 8)
        scan_set_name = "fine_70um_10um_step"
        expected_scan_set = ScanSet(scan_set_name, expected_axes_xy, fast_dimension,
                                    slow_dimension, 0.1, alternate=True, continuous=False,
                                    repeats=1)

        # Actual scan set
        actual_scan_set = scan_runner_part.scan_sets[scan_set_name]

        self.assertEqual(1, len(scan_runner_part.scan_sets))
        self.assertTrue(self.compare_scan_set(expected_scan_set, actual_scan_set))
        self.assertEqual(1, scan_runner_part.scans_configured.value)
        self.assertEqual(ScanRunnerPart.get_enum_label(RunnerStates.CONFIGURED), scan_runner_part.runner_state.value)
        self.assertEqual("Load complete", scan_runner_part.runner_status_message.value)

    @patch('__main__.open')
    def test_loadFile_throws_IOError_for_bad_filepath(self, mock_open):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file opener
        mock_open.side_effect = IOError("Fake IOError")

        # Call loadFile which should throw our IOError
        self.assertRaises(IOError, scan_runner_part.loadFile)
        self.assertEqual(ScanRunnerPart.get_enum_label(RunnerStates.FAULT), scan_runner_part.runner_state.value)
        self.assertEqual("Could not read scan file", scan_runner_part.runner_status_message.value)

    def test_loadFile_throws_YAMLError_for_invalid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        # Mock the file reader method to return a string
        scan_runner_part.get_file_contents = Mock()
        scan_runner_part.get_file_contents.return_value = self.invalid_yaml

        # Call loadFile to parse our mocked string
        self.assertRaises(YAMLError, scan_runner_part.loadFile)
        self.assertEqual(ScanRunnerPart.get_enum_label(RunnerStates.FAULT), scan_runner_part.runner_state.value)
        self.assertEqual("Could not parse scan file", scan_runner_part.runner_status_message.value)

    def test_parse_yaml_parses_valid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        scan_runner_part.parse_yaml(self.good_yaml)

    def test_parse_yaml_throws_YAMLError_for_invalid_YAML(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # Run setup with a Mock registrar
        scan_runner_part.setup(Mock())

        self.assertRaises(YAMLError, scan_runner_part.parse_yaml, self.invalid_yaml)
        self.assertEqual(ScanRunnerPart.get_enum_label(RunnerStates.FAULT), scan_runner_part.runner_state.value)
        self.assertEqual("Could not parse scan file", scan_runner_part.runner_status_message.value)

    def test_get_enum_label_capitalises_state(self):
        expected_label = "Configured"

        self.assertEqual(expected_label, ScanRunnerPart.get_enum_label(RunnerStates.CONFIGURED))

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

    def test_parse_axes_parses_valid_entry(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        entry = {
            'name': "sample_stages",
            'fast_axis': "sample_x",
            'slow_axis': "sample_y",
            'units': "mm"
        }

        scan_runner_part.parse_axes(entry)

        self.assertEqual(1, len(scan_runner_part.axes_sets))

        axes = scan_runner_part.axes_sets['sample_stages']
        self.assertEqual("sample_stages", axes.name)
        self.assertEqual("sample_x", axes.fast_axis)
        self.assertEqual("sample_y", axes.slow_axis)
        self.assertEqual("mm", axes.units)

    def test_parse_axes_throws_KeyError_for_missing_key(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)

        # List of compulsory arguments
        axes_args = {
            'name': "coarse_stages",
            'fast_axis': "sample_x",
            'slow': "sample_y",
            'units': "um"
        }

        # The number of iterations requires is equal to the number of compulsory arguments
        for arg_num in range(len(axes_args)):
            axes_with_missing_arg = {}
            index = 0
            # We want to miss out a different argument each time
            for key in axes_args:
                if index == arg_num:
                    pass
                else:
                    axes_with_missing_arg[key] = axes_args[key]
                index += 1

            self.assertRaises(KeyError, scan_runner_part.parse_axes, axes_with_missing_arg)

    def test_parse_scan_set_2d_parses_for_all_arguments(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # We need to have a set of axes to match
        axes = {
            'name': "sample_stages",
            'fast_axis': "sample_x",
            'slow_axis': "sample_y",
            'units': "mm"
        }
        scan_runner_part.parse_axes(axes)

        # Now we can parse our scan set
        scan_set = {
            'name': "fine_snake_scan",
            'axes': "sample_stages",
            'start_fast': 0.0,
            'stop_fast': 10.0,
            'steps_fast': 25,
            'start_slow': -5.0,
            'stop_slow': 5.0,
            'steps_slow': 10,
            'alternate': True,
            'continuous': False,
            'repeats': 12,
            'duration': 0.5
        }
        scan_runner_part.parse_scan_set_2d(scan_set)

        self.assertEqual(1, len(scan_runner_part.scan_sets))

        parsed_scan_set = scan_runner_part.scan_sets['fine_snake_scan']

        self.assertEqual("fine_snake_scan", parsed_scan_set.name)
        self.assertEqual("sample_stages", parsed_scan_set.axes.name)
        self.assertEqual(0.0, parsed_scan_set.fast_dimension.start)
        self.assertEqual(10.0, parsed_scan_set.fast_dimension.stop)
        self.assertEqual(25, parsed_scan_set.fast_dimension.steps)
        self.assertEqual(-5.0, parsed_scan_set.slow_dimension.start)
        self.assertEqual(5.0, parsed_scan_set.slow_dimension.stop)
        self.assertEqual(10, parsed_scan_set.slow_dimension.steps)
        self.assertEqual(12, parsed_scan_set.repeats)
        self.assertEqual(0.5, parsed_scan_set.duration)
        self.assertTrue(parsed_scan_set.alternate)
        self.assertFalse(parsed_scan_set.continuous)

    def test_parse_scan_set_2d_parses_for_compulsory_arguments(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # We need to have a set of axes to match
        axes = {
            'name': "sample_stages",
            'fast_axis': "sample_x",
            'slow_axis': "sample_y",
            'units': "mm"
        }
        scan_runner_part.parse_axes(axes)

        # Now we can parse our scan set
        scan_set = {
            'name': "fine_snake_scan",
            'axes': "sample_stages",
            'start_fast': 0.0,
            'stop_fast': 10.0,
            'steps_fast': 25,
            'start_slow': -5.0,
            'stop_slow': 5.0,
            'steps_slow': 10,
            'duration': 0.5
        }
        scan_runner_part.parse_scan_set_2d(scan_set)

        self.assertEqual(1, len(scan_runner_part.scan_sets))

        parsed_scan_set = scan_runner_part.scan_sets['fine_snake_scan']

        self.assertEqual("fine_snake_scan", parsed_scan_set.name)
        self.assertEqual("sample_stages", parsed_scan_set.axes.name)
        self.assertEqual(0.0, parsed_scan_set.fast_dimension.start)
        self.assertEqual(10.0, parsed_scan_set.fast_dimension.stop)
        self.assertEqual(25, parsed_scan_set.fast_dimension.steps)
        self.assertEqual(-5.0, parsed_scan_set.slow_dimension.start)
        self.assertEqual(5.0, parsed_scan_set.slow_dimension.stop)
        self.assertEqual(10, parsed_scan_set.slow_dimension.steps)
        self.assertEqual(1, parsed_scan_set.repeats)
        self.assertEqual(0.5, parsed_scan_set.duration)
        self.assertFalse(parsed_scan_set.alternate)
        self.assertTrue(parsed_scan_set.continuous)

    def test_parse_scan_set_2d_throws_KeyError_for_missing_axes(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # Add an example axes
        axes = {
            'name': "sample_stages",
            'fast_axis': "sample_x",
            'slow_axis': "sample_y",
            'units': "mm"
        }
        scan_runner_part.parse_axes(axes)

        # Our scan set uses a different set of axes than the one provided
        scan_set = {
            'name': "fine_snake_scan",
            'axes': "coarse_stages",
            'start_fast': 0.0,
            'stop_fast': 10.0,
            'steps_fast': 25,
            'start_slow': -5.0,
            'stop_slow': 5.0,
            'steps_slow': 10,
            'duration': 0.5
        }

        self.assertRaises(KeyError, scan_runner_part.parse_scan_set_2d, scan_set)

    def test_parse_scan_set_2d_throws_KeyError_for_missing_arguments(self):
        scan_runner_part = ScanRunnerPart(self.name, self.mri)
        # Add the matching axes
        axes = {
            'name': "sample_stages",
            'fast_axis': "sample_x",
            'slow_axis': "sample_y",
            'units': "mm"
        }
        scan_runner_part.parse_axes(axes)

        scan_set_args = {
            'name': "fine_snake_scan",
            'axes': "sample_stages",
            'start_fast': 0.0,
            'stop_fast': 10.0,
            'steps_fast': 25,
            'start_slow': -5.0,
            'stop_slow': 5.0,
            'steps_slow': 10,
            'duration': 0.5
        }

        # The number of iterations requires is equal to the number of compulsory arguments
        for arg_num in range(len(scan_set_args)):
            scan_set_with_missing_arg = {}
            index = 0
            # We want to miss out a different argument each time
            for key in scan_set_args:
                if index == arg_num:
                    pass
                else:
                    scan_set_with_missing_arg[key] = scan_set_args[key]
                index += 1

            self.assertRaises(KeyError, scan_runner_part.parse_scan_set_2d, scan_set_with_missing_arg)
