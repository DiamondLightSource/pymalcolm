import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from annotypes import add_call_types
from ruamel import yaml
from scanpointgenerator import CompoundGenerator, LineGenerator

from malcolm.core import (
    AbortedError,
    NotWriteableError,
    NumberMeta,
    PartRegistrar,
    StringMeta,
    TimeoutError,
    Widget,
    config_tag,
)
from malcolm.modules import builtin
from malcolm.modules.builtin.parts import ChildPart
from malcolm.modules.scanning.util import RunnableStates

from ..hooks import AContext

# Pull re-used annotypes
APartName = builtin.parts.APartName
AMri = builtin.parts.AMri


class EntryType(Enum):
    GENERATOR = 0
    SCAN = 1


class GeneratorType(Enum):
    LINE = 0


class RunnerStates(Enum):
    IDLE = 0
    LOADING = 1
    CONFIGURED = 2
    RUNNING = 3
    FINISHED = 4
    FAULT = 5
    ABORTED = 6


class ScanOutcome(Enum):
    SUCCESS = 0
    TIMEOUT = 1
    NOTWRITEABLE = 2
    ABORTED = 3
    MISCONFIGURED = 4
    FAIL = 5
    OTHER = 99


class Scan:
    def __init__(
        self, name: str, generator: CompoundGenerator, repeats: int = 1
    ) -> None:
        self.name = name
        self.generator = generator
        self.repeats = repeats


class ScanRunnerPart(ChildPart):
    """Used to run sets of scans defined in a YAML file with a scan block"""

    def __init__(self, name: APartName, mri: AMri) -> None:
        super().__init__(name, mri, stateful=False, initial_visibility=True)
        self.runner_config = None
        self.context: Optional[AContext] = None
        self.scan_sets: Dict[str, Scan] = {}

        self.runner_state = StringMeta(
            "Runner state", tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        self.runner_status_message = StringMeta(
            "Runner status message", tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model("Idle")
        self.scan_file = StringMeta(
            "Path to input scan file", tags=[config_tag(), Widget.TEXTINPUT.tag()]
        ).create_attribute_model()
        self.scans_configured = NumberMeta(
            "int64", "Number of configured scans", tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        self.current_scan_set = StringMeta(
            "Current scan set", tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        self.scans_completed = NumberMeta(
            "int64", "Number of scans completed", tags=Widget.TEXTUPDATE.tag()
        ).create_attribute_model()
        self.scan_successes = NumberMeta(
            "int64", "Successful scans", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        self.scan_failures = NumberMeta(
            "int64", "Failed scans", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model()
        self.output_directory = StringMeta(
            "Root output directory (will create a sub-directory inside)",
            tags=[config_tag(), Widget.TEXTINPUT.tag()],
        ).create_attribute_model()

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)

        # Register attributes
        registrar.add_attribute_model(
            "runnerState", self.runner_state, self.runner_state.set_value
        )
        registrar.add_attribute_model(
            "runnerStatusMessage",
            self.runner_status_message,
            self.runner_status_message.set_value,
        )
        registrar.add_attribute_model(
            "scanFile", self.scan_file, self.scan_file.set_value
        )
        registrar.add_attribute_model(
            "scansConfigured", self.scans_configured, self.scans_configured.set_value
        )
        registrar.add_attribute_model(
            "currentScanSet", self.current_scan_set, self.current_scan_set.set_value
        )
        registrar.add_attribute_model(
            "scansCompleted", self.scans_completed, self.scans_completed.set_value
        )
        registrar.add_attribute_model(
            "scanSuccesses", self.scan_successes, self.scan_successes.set_value
        )
        registrar.add_attribute_model(
            "scanFailures", self.scan_failures, self.scan_failures.set_value
        )
        registrar.add_attribute_model(
            "outputDirectory", self.output_directory, self.output_directory.set_value
        )

        # Methods
        registrar.add_method_model(self.loadFile)
        registrar.add_method_model(self.run, needs_context=True)
        registrar.add_method_model(self.abort, needs_context=True)

    def get_file_contents(self) -> str:

        try:
            with open(self.scan_file.value, "r") as input_file:
                return input_file.read()
        except IOError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Could not read scan file")
            raise

    def parse_yaml(self, string: str) -> Any:
        try:
            parsed_yaml = yaml.safe_load(string)
            return parsed_yaml
        except yaml.YAMLError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Could not parse scan file")
            raise

    @staticmethod
    def get_kwargs_from_dict(input_dict, kwargs_list):
        kwargs = {}
        if not isinstance(kwargs_list, list):
            kwargs_list = [kwargs_list]
        for kwarg in kwargs_list:
            if kwarg in input_dict:
                kwargs[kwarg] = input_dict[kwarg]
        return kwargs

    @staticmethod
    def parse_compound_generator(entry: dict) -> CompoundGenerator:
        generators = []
        generators_dict = entry["generators"]
        for generator in generators_dict:
            generators.append(LineGenerator.from_dict(generator["line"]))

        entry["generators"] = generators
        compound_generator = CompoundGenerator.from_dict(entry)
        if compound_generator.duration <= 0.0:
            raise ValueError(
                "Negative generator duration - is it missing from the YAML?"
            )
        return compound_generator

    def parse_scan(self, entry: dict) -> None:
        name = entry["name"]
        generator = self.parse_compound_generator(entry["generator"])
        kwargs = self.get_kwargs_from_dict(entry, "repeats")

        self.scan_sets[name] = Scan(name, generator, **kwargs)

    @staticmethod
    def get_current_datetime(time_separator: str = ":") -> str:
        return datetime.now().strftime(
            "%Y-%m-%d-%H{sep}%M{sep}%S".format(sep=time_separator)
        )

    # noinspection PyPep8Naming
    def loadFile(self) -> None:

        # Update state
        self.set_runner_state(RunnerStates.LOADING)
        self.runner_status_message.set_value("Loading scan file")

        # Read contents of file into string
        file_contents = self.get_file_contents()

        # Parse the string
        parsed_yaml = self.parse_yaml(file_contents)

        # Empty the current dictionaries
        self.scan_sets = {}

        # Parse the configuration
        for item in parsed_yaml:
            key_name = list(item.keys())[0].upper()
            if key_name == EntryType.SCAN.name:
                self.parse_scan(item["scan"])
            else:
                self.set_runner_state(RunnerStates.FAULT)
                self.runner_status_message.value = "Unidentified key in YAML"
                raise ValueError(
                    "Unidentified object in YAML: {key}".format(key=key_name)
                )

        # Count the number of scans configured
        self.update_scans_configured()

        self.set_runner_state(RunnerStates.CONFIGURED)
        self.runner_status_message.set_value("Load complete")

    def update_scans_configured(self) -> None:
        number_of_scans = 0
        for key in self.scan_sets:
            number_of_scans += self.scan_sets[key].repeats
        self.scans_configured.set_value(number_of_scans)

    def create_directory(self, directory: str) -> None:
        try:
            os.mkdir(directory)
        except OSError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Could not create directory")
            raise IOError(
                "ERROR: unable to create directory: {dir}".format(dir=directory)
            )

    def create_and_get_sub_directory(self, root_directory: str) -> str:
        today_str = self.get_current_datetime(time_separator="-")
        sub_directory = "{root}/{scan_mri}-{date}".format(
            root=root_directory, scan_mri=self.mri, date=today_str
        )
        self.create_directory(sub_directory)
        return sub_directory

    def get_root_directory(self):
        root_directory = self.output_directory.value
        if root_directory[-1] == "/":
            root_directory = root_directory[:-1]
        return root_directory

    @add_call_types
    def abort(self, context: AContext) -> None:
        if self.context:
            # Stop the context
            self.context.stop()
            # Stop the current scan
            context.block_view(self.mri).abort()
            # Update status
            self.set_runner_state(RunnerStates.ABORTED)
            self.runner_status_message.set_value("Aborted scans")

    @add_call_types
    def run(self, context: AContext) -> None:

        # Check that we have loaded some scan sets
        if len(self.scan_sets) == 0:
            self.runner_status_message.set_value("No scan file loaded")
            raise ValueError("No scan sets configured. Have you loaded a YAML file?")

        # Root file directory
        root_directory = self.get_root_directory()

        # Sub-directory to create for this run
        sub_directory = self.create_and_get_sub_directory(root_directory)

        # Top-level report filepath
        report_filepath = "{root}/report.txt".format(root=sub_directory)

        # Reset counters and set state
        self.scans_completed.set_value(0)
        self.scan_successes.set_value(0)
        self.scan_failures.set_value(0)
        self.set_runner_state(RunnerStates.RUNNING)

        # Get our scan block and store context
        self.context = context
        scan_block = self.context.block_view(self.mri)

        # Cycle through the scan sets
        for key in self.scan_sets:
            self.run_scan_set(
                self.scan_sets[key], scan_block, sub_directory, report_filepath
            )

        self.set_runner_state(RunnerStates.FINISHED)
        self.current_scan_set.set_value("")
        self.runner_status_message.set_value("Scans complete")

    def create_and_get_set_directory(self, sub_directory: str, set_name: str) -> str:
        set_directory = "{sub_directory}/scanset-{set_name}".format(
            sub_directory=sub_directory, set_name=set_name
        )
        self.create_directory(set_directory)
        return set_directory

    def run_scan_set(
        self,
        scan_set: Scan,
        scan_block: Any,
        sub_directory: str,
        report_filepath: str,
    ) -> None:
        # Update scan set
        self.current_scan_set.set_value(scan_set.name)

        # Directory where to save scans for this set
        set_directory = self.create_and_get_set_directory(sub_directory, scan_set.name)

        # Run each scan
        for scan_number in range(1, scan_set.repeats + 1):
            self.run_scan(
                scan_set.name,
                scan_block,
                set_directory,
                scan_number,
                report_filepath,
                scan_set.generator,
            )

    def create_and_get_scan_directory(
        self, set_directory: str, scan_number: int
    ) -> str:
        scan_directory = "{set_directory}/scan-{scan_number}".format(
            set_directory=set_directory, scan_number=scan_number
        )
        self.create_directory(scan_directory)
        return scan_directory

    @staticmethod
    def scan_is_aborting(scan_block):
        return scan_block.state.value is RunnableStates.ABORTING

    def run_scan(
        self,
        set_name: str,
        scan_block: Any,
        set_directory: str,
        scan_number: int,
        report_filepath: str,
        generator: CompoundGenerator,
    ) -> None:
        self.runner_status_message.set_value(
            "Running {set_name}: {scan_no}".format(
                set_name=set_name, scan_no=scan_number
            )
        )
        assert self.context, "No context found"

        # Make individual scan directory
        scan_directory = self.create_and_get_scan_directory(set_directory, scan_number)

        # Check if scan can be reset or run
        while self.scan_is_aborting(scan_block):
            self.context.sleep(0.1)

        # Run the scan and capture the outcome
        if scan_block.state.value is not RunnableStates.READY:
            scan_block.reset()

        # Configure first
        outcome = None
        try:
            scan_block.configure(generator, fileDir=scan_directory)
        except AssertionError:
            outcome = ScanOutcome.MISCONFIGURED
        except Exception as e:
            outcome = ScanOutcome.MISCONFIGURED
            self.log.error(
                f"Unhandled exception for scan {scan_number} in {set_name}: "
                f"({type(e)}) {e}"
            )

        # Run if configure was successful
        start_time = self.get_current_datetime()
        if outcome is None:
            try:
                scan_block.run()
            except TimeoutError:
                outcome = ScanOutcome.TIMEOUT
            except NotWriteableError:
                outcome = ScanOutcome.NOTWRITEABLE
            except AbortedError:
                outcome = ScanOutcome.ABORTED
            except AssertionError:
                outcome = ScanOutcome.FAIL
            except Exception as e:
                outcome = ScanOutcome.OTHER
                self.log.error(
                    (
                        f"Unhandled exception for scan {scan_number} in {set_name}: "
                        f"({type(e)}) {e}"
                    )
                )
            else:
                outcome = ScanOutcome.SUCCESS

        # Record the outcome
        end_time = self.get_current_datetime()
        report_string = self.get_report_string(
            set_name, scan_number, outcome, start_time, end_time
        )
        self.add_report_line(report_filepath, report_string)

        if outcome is ScanOutcome.SUCCESS:
            self.increment_scan_successes()
        else:
            self.increment_scan_failures()

    def increment_scan_successes(self):
        self.scan_successes.set_value(self.scan_successes.value + 1)
        self.increment_scans_completed()

    def increment_scan_failures(self):
        self.scan_failures.set_value(self.scan_failures.value + 1)
        self.increment_scans_completed()

    def increment_scans_completed(self):
        self.scans_completed.set_value(self.scans_completed.value + 1)

    def get_report_string(
        self,
        set_name: str,
        scan_number: int,
        scan_outcome: ScanOutcome,
        start_time: str,
        end_time: str,
    ) -> str:

        report_str = "{set:<30}{no:<10}{outcome:<14}{start:<20}{end}".format(
            set=set_name,
            no=scan_number,
            outcome=self.get_enum_label(scan_outcome),
            start=start_time,
            end=end_time,
        )
        return report_str

    def add_report_line(self, report_filepath: str, report_string: str) -> None:
        try:
            with open(report_filepath, "a+") as report_file:
                report_file.write(
                    "{report_string}\n".format(report_string=report_string)
                )
        except IOError:
            self.set_runner_state(RunnerStates.FAULT)
            self.runner_status_message.set_value("Error writing report file")
            raise IOError(
                "Could not write to report file {filepath}".format(
                    filepath=report_filepath
                )
            )

    @staticmethod
    def get_enum_label(enum_state: Enum) -> str:
        return enum_state.name.capitalize()

    def set_runner_state(self, runner_state: RunnerStates) -> None:
        self.runner_state.set_value(self.get_enum_label(runner_state))
