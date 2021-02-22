from typing import Any, Dict, Iterable, List, Optional, Tuple, cast

from annotypes import Anno, add_call_types, stringify_error
from scanpointgenerator import (
    CompoundGenerator,
    SquashingExcluder,
    StaticPointGenerator,
)

from malcolm.core import APartName, BadValueError, Future, Put, Request
from malcolm.modules import builtin

from ..hooks import (
    AAxesToMove,
    AbortHook,
    ABreakpoints,
    ACompletedSteps,
    AContext,
    AFileDir,
    AFileTemplate,
    AGenerator,
    APartInfo,
    ConfigureHook,
    PostRunArmedHook,
    PostRunReadyHook,
    PreConfigureHook,
    RunHook,
    SeekHook,
    UInfos,
    UParameterTweakInfos,
    ValidateHook,
)
from ..infos import (
    DatasetProducedInfo,
    DetectorMutiframeInfo,
    ParameterTweakInfo,
    RunProgressInfo,
)
from ..util import ADetectorTable, DetectorTable, RunnableStates

with Anno("The initial value of FramesPerStep for this detector at configure"):
    AInitialFramesPerStep = int

# Pull re-used annotypes into our namespace in case we are subclassed
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

ss = RunnableStates


class DetectorChildPart(builtin.parts.ChildPart):
    """Part controlling a child detector Block that exposes a configure/run
    interface with fileDir and fileTemplate"""

    def __init__(
        self,
        name: APartName,
        mri: AMri,
        initial_visibility: AInitialVisibility = False,
        initial_frames_per_step: AInitialFramesPerStep = 1,
    ) -> None:
        super().__init__(name, mri, initial_visibility)
        # frames per scan step given by the detector table at configure()
        self.initial_frames_per_step = initial_frames_per_step
        self.frames_per_step = initial_frames_per_step
        # Stored between runs
        self.run_future: Optional[Future] = None
        # If it was faulty at init, allow it to exist, and ignore reset commands
        # but don't let it be configured or run
        self.faulty = False

    def setup(self, registrar):
        super().setup(registrar)
        # Hooks
        registrar.hook(ValidateHook, self.on_validate)
        registrar.hook(PreConfigureHook, self.reload)
        registrar.hook(ConfigureHook, self.on_configure)
        registrar.hook(RunHook, self.on_run)
        registrar.hook((PostRunArmedHook, PostRunReadyHook), self.on_post_run)
        registrar.hook(SeekHook, self.on_seek)
        registrar.hook(AbortHook, self.on_abort)

    @add_call_types
    def on_layout(
        self,
        context: AContext,
        ports: builtin.hooks.APortMap,
        layout: builtin.hooks.ALayoutTable,
    ) -> builtin.hooks.ULayoutInfos:
        ret = super().on_layout(context, ports, layout)
        # Tell the controller to expose some extra configure parameters
        configure_info = ConfigureHook.create_info(self.on_configure)
        # Override the detector table defaults and writeable
        rows = []
        if self.visible:
            if self.initial_frames_per_step:
                enable = True
                frames_per_step = self.initial_frames_per_step
            else:
                enable = False
                frames_per_step = 1
            rows.append([enable, self.name, self.mri, 0.0, frames_per_step])
        configure_info.defaults["detectors"] = DetectorTable.from_rows(rows)
        columns = configure_info.metas["detectors"].elements
        columns["name"].set_writeable(False)
        columns["mri"].set_writeable(False)
        assert self.registrar, "No registrar found"
        self.registrar.report(configure_info)
        return ret

    def notify_dispatch_request(self, request: Request) -> None:
        if isinstance(request, Put) and request.path[1] == "design":
            # We have hooked self.reload to PreConfigure, and reload() will
            # set design attribute, so explicitly allow this without checking
            # it is in no_save (as it won't be in there)
            pass
        else:
            super().notify_dispatch_request(request)

    @add_call_types
    def on_init(self, context: AContext) -> None:
        try:
            super().on_init(context)
        except BadValueError:
            self.log.exception(
                f"Detector {self.name} was faulty at init and is not usable"
            )
            self.faulty = True

    @add_call_types
    def on_reset(self, context: AContext) -> None:
        if not self.faulty:
            child = context.block_view(self.mri)
            if child.abort.meta.writeable:
                child.abort()
            super().on_reset(context)

    # Must match those passed in configure() Method, so need to be camelCase
    # noinspection PyPep8Naming
    @add_call_types
    def on_validate(
        self,
        context: AContext,
        part_info: APartInfo,
        generator: AGenerator,
        fileDir: AFileDir,
        detectors: ADetectorTable = None,
        axesToMove: AAxesToMove = None,
        breakpoints: ABreakpoints = None,
        fileTemplate: AFileTemplate = "%s.h5",
    ) -> UParameterTweakInfos:
        # Work out if we are taking part
        enable, frames_per_step, kwargs = self._configure_args(
            generator, fileDir, detectors, axesToMove, breakpoints, fileTemplate
        )
        ret = []
        tweak_detectors = False
        assert detectors, "No detectors"
        if self.name not in detectors.name:
            # There isn't a row for us, so add one in on validate, it will be
            # disabled but that is truthful
            tweak_detectors = True

        child = context.block_view(self.mri)
        takes_exposure = "exposure" in child.validate.meta.takes.elements

        def do_validate(**params):
            if not takes_exposure:
                params.pop("exposure", None)
            try:
                return child.validate(**params)
            except Exception as e:
                raise BadValueError(
                    "Validate of %s failed: %s" % (self.mri, stringify_error(e))
                )

        # Check something else is multiplying out triggers
        multiframe: List[DetectorMutiframeInfo] = []
        info: DetectorMutiframeInfo
        for info in DetectorMutiframeInfo.filter_values(part_info):
            if cast(DetectorMutiframeInfo, info).mri == self.mri:
                multiframe.append(info)

        if enable:
            if self.faulty:
                raise BadValueError(
                    "Detector %s was faulty at init and is unusable. If the "
                    "detector is now working please restart Malcolm" % self.name
                )
            # Check that if we are told to set exposure that we take it
            if "exposure" in kwargs and not multiframe and not takes_exposure:
                raise BadValueError("Detector %s doesn't take exposure" % self.name)
            # If asked to guess frames per step, do so
            if frames_per_step < 1:
                if kwargs.get("exposure", 0) == 0:
                    # Asked to guess both
                    frames_per_step = 1
                else:
                    # Exposure given, so run a validate once without the
                    # mutiplier and see what the detector gives us
                    exposure = kwargs.pop("exposure")
                    returns = do_validate(**kwargs)
                    dead_time = generator.duration - returns["exposure"]
                    frames_per_step = generator.duration // (exposure + dead_time)
                    kwargs["exposure"] = exposure
                tweak_detectors = True
            if frames_per_step > 1 and not multiframe:
                raise BadValueError(
                    "There are no trigger multipliers setup for Detector '%s' "
                    "so framesPerStep can only be 0 or 1 for this row in the "
                    "detectors table" % self.name
                )
            # This is a Serializable with the correct entries
            returns = do_validate(**kwargs)
            # Add in the exposure in case it is returned
            exposure = kwargs.setdefault("exposure", 0.0)
            # TODO: this will fail if we split across 2 Malcolm processes as
            # scanpointgenerators don't compare equal, but we don't want to
            # serialize everything as that is expensive for arrays
            for k in returns:
                v = returns[k]
                if kwargs.get(k, v) != v:
                    if k == "exposure":
                        exposure = v
                        tweak_detectors = True
                    else:
                        ret.append(ParameterTweakInfo(k, v))
        else:
            exposure = 0.0
        if tweak_detectors:
            # Detector table changed, make a new onw
            det_row = [enable, self.name, self.mri, exposure, frames_per_step]
            rows = []
            assert detectors, "No detectors"
            append_det_row = True
            for row in detectors.rows():
                if row[1] == self.name:
                    rows.append(det_row)
                    append_det_row = False
                else:
                    rows.append(row)
            if append_det_row:
                rows.append(det_row)
            new_detectors = DetectorTable.from_rows(rows)
            ret.append(ParameterTweakInfo("detectors", new_detectors))
        return ret

    def _configure_args(
        self,
        generator: AGenerator,
        file_dir: AFileDir,
        detectors: ADetectorTable = None,
        axes_to_move: AAxesToMove = None,
        breakpoints: ABreakpoints = None,
        file_template: AFileTemplate = "%s.h5",
    ) -> Tuple[bool, int, Dict[str, Any]]:
        # Check the detector table to see what we need to do
        assert detectors, "No detectors"
        for enable, name, mri, exposure, frames in detectors.rows():
            if name == self.name and enable:
                # Found a row saying to take part
                assert mri == self.mri, "%s has mri %s, passed %s" % (
                    name,
                    self.mri,
                    mri,
                )
                break
        else:
            # Didn't find a row or no frames, don't take part
            return False, 0, {}
        # If we had more than one frame per point, multiply out
        if frames > 1:
            axis_name = name + "_frames_per_step"
            axes_to_move = list(cast(Iterable, axes_to_move)) + [axis_name]
            # We need to multiply up the last dimension by frames
            serialized = dict(generator.to_dict())
            serialized["generators"] = list(serialized["generators"]) + [
                StaticPointGenerator(frames, axes=[axis_name])
            ]
            # Squash it down with the axes of the fastest generator
            squash_axes = list(generator.generators[-1].axes) + [axis_name]
            serialized["excluders"] = list(serialized["excluders"]) + [
                SquashingExcluder(axes=squash_axes)
            ]
            # Divide it down
            serialized["duration"] = float(serialized["duration"]) / frames
            generator = CompoundGenerator.from_dict(serialized)
        kwargs = dict(
            generator=generator,
            axesToMove=axes_to_move,
            breakpoints=breakpoints,
            fileDir=file_dir,
            # formatName is the unique part of the HDF filename, so use the part
            # name for this
            formatName=self.name,
            fileTemplate=file_template,
        )
        if exposure > 0.0:
            kwargs["exposure"] = exposure
        return enable, frames, kwargs

    # Must match those passed in configure() Method, so need to be camelCase
    # noinspection PyPep8Naming
    @add_call_types
    def on_configure(
        self,
        context: AContext,
        generator: AGenerator,
        fileDir: AFileDir,
        detectors: ADetectorTable = None,
        axesToMove: AAxesToMove = None,
        breakpoints: ABreakpoints = None,
        fileTemplate: AFileTemplate = "%s.h5",
    ) -> UInfos:
        # Work out if we are taking part
        enable, self.frames_per_step, kwargs = self._configure_args(
            generator, fileDir, detectors, axesToMove, breakpoints, fileTemplate
        )
        if not enable:
            # We aren't taking part in the scan
            self.frames_per_step = 0
            return None
        else:
            assert self.frames_per_step > 0, (
                "Zero frames per step for %s, this shouldn't happen" % self.name
            )
        child = context.block_view(self.mri)
        if (
            "exposure" in kwargs
            and "exposure" not in child.configure.meta.takes.elements
        ):
            kwargs.pop("exposure")
        child.configure(**kwargs)
        # Report back any datasets the child has to our parent
        assert hasattr(child, "datasets"), (
            "Detector %s doesn't have a dataset table, did you add a "
            "scanning.parts.DatasetTablePart to it?" % self.mri
        )
        datasets_table = child.datasets.value
        info_list = [DatasetProducedInfo(*row) for row in datasets_table.rows()]
        return info_list

    @add_call_types
    def on_run(self, context: AContext) -> None:
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.completedSteps.subscribe_value(self.update_completed_steps)
        bad_states = [ss.DISABLING, ss.ABORTING, ss.FAULT]
        match_future = child.when_value_matches_async("state", ss.POSTRUN, bad_states)
        if child.state.value == ss.ARMED:
            self.run_future = child.run_async()
        else:
            child.resume()
        try:
            context.wait_all_futures(match_future)
        except BadValueError:
            # If child went into Fault state, raise the friendlier run_future
            # exception
            if child.state.value == ss.FAULT:
                assert self.run_future, "No run future"
                raise self.run_future.exception()
            else:
                raise

    @add_call_types
    def on_post_run(self, context: AContext) -> None:
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        context.wait_all_futures(self.run_future)

    @add_call_types
    def on_seek(self, context: AContext, completed_steps: ACompletedSteps) -> None:
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        # Clear out the update_completed_steps and match_future subscriptions
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.pause(lastGoodStep=completed_steps)

    @add_call_types
    def on_abort(self, context: AContext) -> None:
        child = context.block_view(self.mri)
        child.abort()

    def update_completed_steps(self, value: int) -> None:
        assert self.registrar, "No registrar"
        self.registrar.report(RunProgressInfo(value // self.frames_per_step))
