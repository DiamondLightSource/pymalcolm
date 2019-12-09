import os
from datetime import datetime
from ruamel import yaml
from enum import Enum
from cothread import cothread

from annotypes import add_call_types

from malcolm.core import AttributeModel, PartRegistrar, NumberMeta, \
    StringMeta, config_tag, Widget, TimeoutError, NotWriteableError, \
    AbortedError
from malcolm.modules import builtin
from malcolm.modules.scanning.util import RunnableStates
from ..hooks import AContext, AGenerator

from scanpointgenerator import CompoundGenerator, LineGenerator

# Pull re-used annotypes
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class EntryType(Enum):
    AXES = 0
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
    ABORTED = 3
    OTHER = 99


class ScanDimension:

    def __init__(self, start, stop, steps):
        # type: (float, float, int) -> None
        self.start = start
        self.stop = stop
        self.steps = steps

    def __str__(self):
        return "ScanDimension({start}, {stop}, {steps})".format(
            start=self.start, stop=self.stop, steps=self.steps
        )


class Axes:

    def __init__(self, name, fast_axis, slow_axis, units):
        # type: (str, str, str, str) -> None
        self.name = name
        self.fast_axis = fast_axis
        self.slow_axis = slow_axis
        self.units = units


class ScanSet:

    def __init__(
            self, name, axes, fast_dimension, slow_dimension,
            duration, alternate, continuous, repeats):
        # type: (str, Axes, ScanDimension, ScanDimension, float, bool, bool, int) -> None
        self.name = name
        self.axes = axes
        self.fast_dimension = fast_dimension
        self.slow_dimension = slow_dimension
        self.duration = duration
        self.alternate = alternate
        self.continuous = continuous
        self.repeats = repeats

    def get_compound_generator(self):
        # type: () -> AGenerator
        slow_line_generator = LineGenerator(
            self.axes.slow_axis,
            self.axes.units,
            self.slow_dimension.start,
            self.slow_dimension.stop,
            self.slow_dimension.steps)
        fast_line_generator = LineGenerator(
            self.axes.fast_axis,
            self.axes.units,
            self.fast_dimension.start,
            self.fast_dimension.stop,
            self.fast_dimension.steps,
            alternate=self.alternate)

        generator = CompoundGenerator(
            [slow_line_generator, fast_line_generator],
            [],
            [],
            self.duration,
            continuous=self.continuous)

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
        super(ScanRunnerPart, self).__init__(
            name, mri, stateful=False, initial_visibility=True)
        self.runner_config = None
        self.axes_sets = {}
        self.scan_sets = {}

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ScanRunnerPart, self).setup(registrar)

        self.runner_state = StringMeta(
            "Runner state",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        registrar.add_attribute_model(
            "runnerState",
            self.runner_state,
            self.runner_state.set_value)

        self.runner_status_message = StringMeta(
            "Runner status message",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        registrar.add_attribute_model(
            "runnerStatusMessage",
            self.runner_status_message,
            self.runner_status_message.set_value)

        self.scan_file = StringMeta(
            "Path to input scan file",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "scanFile",
            self.scan_file,
            self.scan_file.set_value)

        self.scans_configured = NumberMeta(
            "int64", "Number of scans configured",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model(
            "scansConfigured",
            self.scans_configured,
            self.scans_configured.set_value)

        self.current_scan_set = StringMeta(
            "Current scan set",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model(
            "currentScanSet",
            self.current_scan_set,
            self.current_scan_set.set_value)

        self.scans_completed = NumberMeta(
            "int64", "Number of scans completed",
            tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        registrar.add_attribute_model(
            "scansCompleted",
            self.scans_completed,
            self.scans_completed.set_value)

        self.scan_successes = NumberMeta(
            "int64", "Successful scans",
            tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "scanSuccesses",
            self.scan_successes,
            self.scan_successes.set_value)

        self.scan_failures = NumberMeta(
            "int64", "Failed scans",
            tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "scanFailures",
            self.scan_failures,
            self.scan_failures.set_value)

        self.output_directory = StringMeta(
            "Root output directory (will create a sub-directory inside)",
            tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        registrar.add_attribute_model(
            "outputDirectory",
            self.output_directory,
            self.output_directory.set_value)

        # Methods
        registrar.add_method_model(self.loadFile)
        registrar.add_method_model(self.run, needs_context=True)

    def get_file_contents(self):
        # type: () -> str

        try:
            with open(self.scan_file.value, "r") as input_file:
                return input_file.read()
        except IOError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Could not read scan file")
            raise IOError("Could not read scan file")

    def parse_yaml(self, string):
        # type: (str) -> ...
        try:
            parsed_yaml = yaml.safe_load(string)
            return parsed_yaml
        except yaml.YAMLError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Could not parse scan file")
            raise yaml.YAMLError("Could not parse scan file")

    def parse_axes(self, entry):
        name = entry["name"]
        fast_axis = entry["fast_axis"]
        slow_axis = entry["slow_axis"]
        units = entry["units"]

        self.axes_sets[name] = Axes(name, fast_axis, slow_axis, units)

    def parse_scan_set_2d(self, entry):
        name = entry["name"]
        axes_name = entry["axes"]
        start_fast = entry["start_fast"]
        start_slow = entry["start_slow"]
        stop_fast = entry["stop_fast"]
        stop_slow = entry["stop_slow"]
        steps_fast = entry["steps_fast"]
        steps_slow = entry["steps_slow"]
        duration = entry["duration"]
        if 'alternate' in entry:
            alternate = entry["alternate"]
        else:
            alternate = False
        if 'continuous' in entry:
            continuous = entry["continuous"]
        else:
            continuous = True
        if 'repeats' in entry:
            repeats = entry["repeats"]
        else:
            repeats = 1

        fast_dimension = ScanDimension(
            start_fast, stop_fast, int(steps_fast))
        slow_dimension = ScanDimension(
            start_slow, stop_slow, int(steps_slow))
        self.scan_sets[name] = ScanSet(
            name, self.axes_sets[axes_name], fast_dimension, slow_dimension,
            duration, alternate, continuous, repeats)

    # noinspection PyPep8Naming
    def loadFile(self):
        # type: () -> None

        # Update state
        self.set_runner_state(RunnerStates.LOADING)
        self.runner_status_message.set_value("Loading scan file")

        # Read contents of file into string
        file_contents = self.get_file_contents()

        # Parse the string
        parsed_yaml = self.parse_yaml(file_contents)

        # Empty the current dictionaries
        self.axes_sets = {}
        self.scan_sets = {}

        # Parse the configuration
        for item in parsed_yaml:
            key_name = list(item.keys())[0].upper()
            if key_name == EntryType.AXES.name:
                self.parse_axes(item['axes'])

            elif key_name == EntryType.SCANSET2D.name:
                self.parse_scan_set_2d(item['ScanSet2d'])

        # Count the number of scans configured
        self.update_scans_configured()

        self.set_runner_state(RunnerStates.CONFIGURED)
        self.runner_status_message.set_value("Load complete")

    def update_scans_configured(self):
        number_of_scans = 0
        for key in self.scan_sets:
            number_of_scans += self.scan_sets[key].repeats
        self.scans_configured.set_value(number_of_scans)

    def create_directory(self, directory):
        try:
            os.mkdir(directory)
        except OSError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value(
                "Could not create directory")
            raise IOError(
                "ERROR: unable to create directory: {dir}".format(
                    dir=directory
                ))

    def create_and_get_sub_directory(self, root_directory):
        today_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        sub_directory = "{root}/{scan_mri}-{date}".format(
            root=root_directory, scan_mri=self.mri, date=today_str)
        self.create_directory(sub_directory)
        return sub_directory

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None

        # Check that we have loaded some scan sets
        if len(self.scan_sets) == 0:
            self.runner_status_message.set_value("No scan file loaded")
            raise ValueError(
                "No scan sets configured. Have you loaded a YAML file?")

        # Root file directory
        root_directory = self.output_directory.value
        if root_directory[-1] == "/":
            root_directory = root_directory[:-1]

        # Sub-directory to create for this run
        sub_directory = self.create_and_get_sub_directory(root_directory)

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
            self.run_scan_set(
                self.scan_sets[key],
                scan_block,
                sub_directory,
                report_filepath)

        self.set_runner_state(RunnerStates.FINISHED)
        self.current_scan_set.set_value("")
        self.runner_status_message.set_value("Scans complete")

    def create_and_get_set_directory(self, sub_directory, set_name):
        set_directory = "{sub_directory}/scanset-{set_name}".format(
            sub_directory=sub_directory, set_name=set_name)
        self.create_directory(set_directory)
        return set_directory

    def run_scan_set(self, scan_set, scan_block, sub_directory,
                     report_filepath):
        # Update scan set
        self.current_scan_set.set_value(scan_set.name)

        # Get the compound generator
        generator = scan_set.get_compound_generator()

        # Directory where to save scans for this set
        set_directory = self.create_and_get_set_directory(
            sub_directory, scan_set.name)

        # Run each scan
        for number in range(1, scan_set.repeats+1):
            self.run_scan(
                scan_set.name,
                scan_block,
                set_directory,
                number,
                report_filepath,
                generator)

    def create_and_get_scan_directory(self, set_directory, scan_number):
        scan_directory = "{set_directory}/scan-{scan_number}".format(
            set_directory=set_directory, scan_number=scan_number)
        self.create_directory(scan_directory)
        return scan_directory

    def run_scan(self, set_name, scan_block, set_directory,
                 scan_number, report_filepath, generator):
        self.runner_status_message.set_value(
            "Running {set_name}: {scan_no}".format(
                set_name=set_name, scan_no=scan_number
            ))

        # Make individual scan directory
        scan_directory = self.create_and_get_scan_directory(
            set_directory, scan_number)

        # Check if scan can be reset or run
        while scan_block.state.value is RunnableStates.ABORTING:
            cothread.Sleep(0.1)

        # Run the scan and capture the outcome
        start_time = None
        if scan_block.state.value is not RunnableStates.READY:
            scan_block.reset()
        try:
            scan_block.configure(generator, fileDir=scan_directory)
            start_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
            scan_block.run()
        except TimeoutError:
            self.increment_scan_failures()
            outcome = ScanOutcome.TIMEOUT
        except NotWriteableError:
            self.increment_scan_failures()
            outcome = ScanOutcome.NOTWRITEABLE
        except AbortedError:
            self.increment_scan_failures()
            outcome = ScanOutcome.ABORTED
        except Exception as e:
            self.increment_scan_failures()
            outcome = ScanOutcome.OTHER
            self.log.warning(
                "Unhandled exception for scan {no} in {set}: {e}".format(
                    no=scan_number,
                    set=set_name,
                    e=e
                ))
        else:
            self.increment_scan_successes()
            outcome = ScanOutcome.SUCCESS

        # Record the outcome
        self.add_report_line(
            report_filepath, set_name, scan_number, outcome, start_time)
        if outcome is ScanOutcome.SUCCESS:
            self.increment_scan_successes()
        else:
            self.increment_scan_failures()

    def increment_scan_successes(self):
        self.scan_successes.set_value(self.scan_successes.value+1)
        self.increment_scans_completed()

    def increment_scan_failures(self):
        self.scan_failures.set_value(self.scan_failures.value+1)
        self.increment_scans_completed()

    def increment_scans_completed(self):
        self.scans_completed.set_value(self.scans_completed.value+1)

    def get_report_string(
            self, set_name, scan_number, scan_outcome, start_time, end_time):
        report_str = "{set:<30}{scan_no:<10}{outcome:<13}{start:<20}{end}".format(
            set=set_name,
            scan_no=scan_number,
            outcome=self.get_enum_label(scan_outcome),
            start=start_time,
            end=end_time
        )
        return report_str

    def add_report_line(self, report_filepath, set_name,
                        scan_number, scan_outcome, start_time):
        report_time = datetime.now().strftime("%Y-%m-%d-%H:%M:%S")
        try:
            with open(report_filepath, "a+") as report_file:
                report_string = self.get_report_string(
                    set_name,
                    scan_number,
                    scan_outcome,
                    start_time,
                    report_time
                )
                report_file.write(
                    "{report_string}\n".format(report_string=report_string))
        except IOError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Error writing report file")
            raise IOError(
                "Could not write to report file {filepath}".format(
                    filepath=report_filepath
                ))

    @staticmethod
    def get_enum_label(enum_state):
        return enum_state.name.capitalize()

    def set_runner_state(self, runner_state):
        self.runner_state.set_value(self.get_enum_label(runner_state))
