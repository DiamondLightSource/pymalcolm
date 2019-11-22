import os
from datetime import datetime
from ruamel import yaml
from enum import Enum
import itertools


from annotypes import add_call_types

from malcolm.core import AttributeModel, PartRegistrar, NumberMeta, \
    StringMeta, config_tag, Widget, TimeoutError, NotWriteableError
from malcolm.modules import builtin
from malcolm.modules.builtin.util import StatefulStates
from ..hooks import AContext

from scanpointgenerator import CompoundGenerator, LineGenerator

# Pull re-used annotypes
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class EntryType(Enum):
    SCANNABLE = 0
    SCANSET2D = 1


class RunnerStates(Enum):
    IDLE = 0
    LOADING = 1
    CONFIGURED = 2
    RUNNING = 3
    FINISHED = 4
    FAULT = 5


class ScanOutcome(Enum):
    SUCCESS = 0
    TIMEOUT = 1
    NOTWRITEABLE = 2
    OTHER = 3


class ScanDimension:

    def __init__(self, start, stop, steps):
        # type: (str, str, str) -> None
        self.start = start
        self.stop = stop
        self.steps = steps


class Scannable:

    def __init__(self, name, fast_axis, slow_axis, units):
        # type: (str, str, str, str) -> None
        self.name = name
        self.fast_axis = fast_axis
        self.slow_axis = slow_axis
        self.units = units


class ScanSet:

    def __init__(
            self, name, scannable_name, fast_dimension, slow_dimension,
            duration, alternate=False, continuous=True, repeats=1):
        # type: (str, str, ScanDimension, ScanDimension, float, bool, bool, int) -> None
        self.name = name
        self.scannable_name = scannable_name
        self.fast_dimension = fast_dimension
        self.slow_dimension = slow_dimension
        self.duration = duration
        self.alternate = alternate
        self.continuous = continuous
        self.repeats = repeats

    def get_compound_generator(self, scannable):
        slow_line_generator = LineGenerator(
            scannable.fast_axis, scannable.units, self.slow_dimension.start, self.slow_dimension.stop,
            self.slow_dimension.steps)
        fast_line_generator = LineGenerator(
            scannable.slow_axis, scannable.units, self.fast_dimension.start, self.fast_dimension.stop,
            self.fast_dimension.steps,
            alternate=self.alternate)
        generator = CompoundGenerator(
            [slow_line_generator, fast_line_generator], [], [], self.duration, continuous=self.continuous)
        return generator


class ScanRunnerPart(builtin.parts.ChildPart):
    """Used to run sets of scans defined in a YAML file with a scan block"""

    # Attributes
    runner_state = None  # type: AttributeModel
    runner_status_message = None  # type: AttributeModel
    scans_configured = None  # type: AttributeModel
    scans_completed = None  # type: AttributeModel
    scan_file = None  # type: AttributeModel
    scan_successes = None  # type: AttributeModel
    scan_failures = None  # type: AttributeModel
    current_scan_set = None  # type: AttributeModel
    output_directory = None  # type: AttributeModel

    def __init__(self, name, mri):
        # type: (APartName, AMri, AMri) -> None
        super(ScanRunnerPart, self).__init__(name, mri, stateful=False, initial_visibility=True)
        self.runner_config = None
        self.scannables = {}
        self.scan_sets = {}

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ScanRunnerPart, self).setup(registrar)

        self.runner_state = StringMeta(
            "Runner state",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        registrar.add_attribute_model("runnerState", self.runner_state, self.runner_state.set_value)

        self.runner_status_message = StringMeta(
            "Runner status message",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        registrar.add_attribute_model("runnerStatusMessage", self.runner_status_message, self.runner_status_message.set_value)

        self.scan_file = StringMeta(
            "Path to input scan file",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model("scanFile", self.scan_file, self.scan_file.set_value)

        self.scans_configured = NumberMeta(
            "int64", "Number of scans configured",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model("scansConfigured", self.scans_configured, self.scans_configured.set_value)

        self.current_scan_set = StringMeta(
            "Current scan set",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model("currentScanSet", self.current_scan_set, self.current_scan_set.set_value)

        self.scans_completed = NumberMeta(
            "int64", "Number of scans completed",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model("scansCompleted", self.scans_completed, self.scans_completed.set_value)

        self.scan_successes = NumberMeta(
            "int64", "Successful scans",
            tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model("scanSuccesses", self.scan_successes, self.scan_successes.set_value)

        self.scan_failures = NumberMeta(
            "int64", "Failed scans",
            tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model("scanFailures", self.scan_failures, self.scan_failures.set_value)

        self.output_directory = StringMeta(
            "Root output directory (will create a sub-directory inside)",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model("outputDirectory", self.output_directory, self.output_directory.set_value)

        # Methods
        registrar.add_method_model(self.loadFile)
        registrar.add_method_model(self.run, needs_context=True)

    # noinspection PyPep8Naming
    def loadFile(self):
        # type: (...) -> None

        # Update state
        self.set_runner_state(RunnerStates.LOADING)
        self.runner_status_message.set_value("Loading scan file")

        with open(self.scan_file.value, "r") as input_file:
            try:
                self.runner_config = yaml.load(input_file, Loader=yaml.Loader)
            except yaml.YAMLError:
                self.set_runner_state(RunnerStates.FAULT)
                self.runner_status_message.set_value("Could not parse file")

        # Empty the current dictionaries
        self.scannables = {}
        self.scan_sets = {}

        # Parse the configuration
        for item in self.runner_config:
            key_name = item.keys()[0].upper()
            if key_name == EntryType.SCANNABLE.name:
                entry = item["scannable"]
                name = entry["name"]
                fast_axis = entry["fast_axis"]
                slow_axis = entry["slow_axis"]
                units = entry["units"]
                self.scannables[name] = Scannable(name, fast_axis, slow_axis, units)

            elif key_name == EntryType.SCANSET2D.name:
                entry = item["ScanSet2d"]
                name = entry["name"]
                scannable = entry["scannable"]
                start_fast = entry["start_fast"]
                start_slow = entry["start_slow"]
                stop_fast = entry["stop_fast"]
                stop_slow = entry["stop_slow"]
                steps_fast = entry["steps_fast"]
                steps_slow = entry["steps_slow"]
                alternate = entry["alternate"]
                continuous = entry["continuous"]
                repeats = entry["repeats"]
                duration = entry["duration"]

                fast_dimension = ScanDimension(start_fast, stop_fast, steps_fast)
                slow_dimension = ScanDimension(start_slow, stop_slow, steps_slow)
                self.scan_sets[name] = ScanSet(name, scannable, fast_dimension, slow_dimension, duration,
                                               alternate=alternate, continuous=continuous, repeats=repeats)

        # Count the number of scans configured
        self.update_scans_configured()

        self.set_runner_state(RunnerStates.CONFIGURED)
        self.runner_status_message.set_value("Load complete")

    def update_scans_configured(self):
        number_of_scans = 0
        for key in self.scan_sets:
            number_of_scans += self.scan_sets[key].repeats
        self.scans_configured.set_value(number_of_scans)

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None

        # Check that we have loaded some scan sets
        if len(self.scan_sets) == 0:
            self.runner_status_message.set_value("No scan file loaded")
            raise ValueError("No scan sets configured. Have you loaded a YAML file?")

        # Root file directory
        root_directory = self.output_directory.value
        if root_directory[-1] == "/":
            root_directory = root_directory[:-1]

        # Sub-directory to create for this run
        today_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        sub_directory = "{root}/{scan_mri}-{date}".format(root=root_directory, scan_mri=self.mri, date=today_str)
        try:
            os.mkdir(sub_directory)
        except OSError:
            self.runner_status_message.set_value("Could not create subdirectory")
            raise IOError("ERROR: unable to create sub directory: {dir}".format(dir=sub_directory))

        # Top-level report filepath
        report_filepath = "{root}/report.txt".format(root=sub_directory)

        # Reset counters and set state
        self.scans_completed.set_value(0)
        self.scan_successes.set_value(0)
        self.scan_failures.set_value(0)
        self.set_runner_state(RunnerStates.RUNNING)

        # Get our scan block
        scan_block = context.block_view(self.mri)

        # Cycle through the scan sets
        for key in self.scan_sets:
            self.run_scan_set(self.scan_sets[key], scan_block, sub_directory, report_filepath)

        self.set_runner_state(RunnerStates.FINISHED)
        self.current_scan_set.set_value("")
        self.runner_status_message.set_value("Scans complete")

    def run_scan_set(self, scan_set, scan_block, sub_directory, report_filepath):
        # Update scan set
        self.current_scan_set.set_value(scan_set.name)

        # Find the matching scannable
        scannable = None
        try:
            scannable = self.scannables[scan_set.scannable_name]
        except KeyError:
            self.runner_status_message.set_value("scannable name error")
            raise KeyError("Could not find scannable matching {key}".format(key=scan_set.scannable_name))

        # Get the compound generator
        generator = scan_set.get_compound_generator(scannable)
        print("\nGenerator:")
        print(generator)

        # Directory where to save scans for this set
        set_directory = "{sub_directory}/scanset-{set_name}".format(
            sub_directory=sub_directory, set_name=scan_set.name)
        try:
            os.mkdir(set_directory)
        except OSError:
            self.runner_status_message.set_value("Could not create scanset dir")
            raise IOError("ERROR: unable to create sub directory: {dir}".format(dir=sub_directory))

        # Run each scan
        for number in range(1, scan_set.repeats+1):
            print("Running {set_name} scan {number}".format(set_name=scan_set.name, number=number))
            self.run_scan(scan_set.name, scan_block, set_directory, number, report_filepath, generator)

    def run_scan(self, set_name, scan_block, set_directory, scan_number, report_filepath, generator):
        self.runner_status_message.set_value("Running {set_name}: {scan_no}".format(
            set_name=set_name, scan_no=scan_number))

        # Make individual scan directory
        scan_path = "{set_directory}/scan-{scan_number}".format(
            set_directory=set_directory, scan_number=scan_number)
        try:
            os.mkdir(scan_path)
        except OSError:
            self.runner_status_message.set_value("Could not create scan dir")
            raise IOError("ERROR: unable to create sub directory: {dir}".format(dir=scan_path))

        # Run the scan
        if scan_block.state.value is not StatefulStates.READY:
            scan_block.reset()
        try:
            scan_block.configure(generator, fileDir=scan_path)
            scan_block.run()
        except TimeoutError:
            self.increment_scan_failures()
            self.add_report_line(report_filepath, set_name, scan_number, ScanOutcome.TIMEOUT)
        except NotWriteableError:
            self.increment_scan_failures()
            self.add_report_line(report_filepath, set_name, scan_number, ScanOutcome.NOTWRITEABLE)
        except Exception as e:
            print("Warning: unhandled scan exception: {exception}".format(exception=e))
            self.increment_scan_failures()
            self.add_report_line(report_filepath, set_name, scan_number, ScanOutcome.OTHER)
        else:
            self.increment_scan_successes()
            self.add_report_line(report_filepath, set_name, scan_number, ScanOutcome.SUCCESS)

    def increment_scan_successes(self):
        self.scan_successes.set_value(self.scan_successes.value+1)
        self.increment_scans_completed()

    def increment_scan_failures(self):
        self.scan_failures.set_value(self.scan_failures.value+1)
        self.increment_scans_completed()

    def increment_scans_completed(self):
        self.scans_completed.set_value(self.scans_completed.value+1)

    def add_report_line(self, report_filepath, set_name, scan_number, scan_state):
        try:
            with open(report_filepath, "a+") as report_file:
                report_file.write("{set:<25}{scan_no:<10}{state}\n".format(
                    set=set_name, scan_no=scan_number, state=self.get_enum_label(scan_state)))
        except IOError:
            self.runner_status_message.set_value("Error writing report file")
            raise IOError("Could not write to report file {filepath}".format(filepath=report_filepath))

    @staticmethod
    def get_enum_label(enum_state):
        return enum_state.name.capitalize()

    def set_runner_state(self, runner_state):
        self.runner_state.set_value(self.get_enum_label(runner_state))
