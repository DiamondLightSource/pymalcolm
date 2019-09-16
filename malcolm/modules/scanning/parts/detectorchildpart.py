from annotypes import add_call_types, Anno, Any, TYPE_CHECKING, stringify_error
from scanpointgenerator import StaticPointGenerator, SquashingExcluder, \
    CompoundGenerator

from malcolm.core import BadValueError, APartName, Future, Put, Request
from malcolm.modules import builtin
from ..infos import DatasetProducedInfo, DetectorMutiframeInfo
from ..hooks import ConfigureHook, PostRunArmedHook, \
    SeekHook, RunHook, ResumeHook, ACompletedSteps, AContext, ValidateHook, \
    UParameterTweakInfos, PostRunReadyHook, AbortHook, PreConfigureHook, \
    AGenerator, AAxesToMove, UInfos, AFileDir, AFileTemplate, APartInfo
from ..infos import ParameterTweakInfo, RunProgressInfo
from ..util import RunnableStates, DetectorTable

if TYPE_CHECKING:
    from typing import Dict, Tuple


with Anno("The detectors that should be active and their exposures"):
    ADetectorTable = DetectorTable
with Anno("The initial value of FramesPerStep for this detector at configure"):
    AInitialFramesPerStep = int

# Pull re-used annotypes into our namespace in case we are subclassed
APartName = APartName
AMri = builtin.parts.AMri
AInitialVisibility = builtin.parts.AInitialVisibility

ss = RunnableStates


class DetectorChildPart(builtin.parts.ChildPart):
    """Part controlling a child detector Block that exposes a configure/run
    interface with fileDir and fileTemplate"""

    def __init__(self,
                 name,  # type: APartName
                 mri,  # type: AMri
                 initial_visibility=False,  # type: AInitialVisibility
                 initial_frames_per_step=1,  # type: AInitialFramesPerStep
                 ):
        # type: (...) -> None
        super(DetectorChildPart, self).__init__(name, mri, initial_visibility)
        # frames per scan step given by the detector table at configure()
        self.frames_per_step = initial_frames_per_step
        # Stored between runs
        self.run_future = None  # type: Future

    def setup(self, registrar):
        super(DetectorChildPart, self).setup(registrar)
        # Hooks
        registrar.hook(ValidateHook, self.validate)
        registrar.hook(PreConfigureHook, self.reload)
        registrar.hook(ConfigureHook, self.configure)
        registrar.hook((RunHook, ResumeHook), self.run)
        registrar.hook((PostRunArmedHook, PostRunReadyHook), self.post_run)
        registrar.hook(SeekHook, self.seek)
        registrar.hook(AbortHook, self.abort)
        # Tell the controller to expose some extra configure parameters
        configure_info = ConfigureHook.create_info(self.configure)
        # Override the detector table defaults and writeable
        configure_info.defaults["detectors"] = DetectorTable.from_rows(
            [(self.name, self.mri, 0.0, self.frames_per_step)])
        columns = configure_info.metas["detectors"].elements
        columns["name"].set_writeable(False)
        columns["mri"].set_writeable(False)
        registrar.report(configure_info)

    def notify_dispatch_request(self, request):
        # type: (Request) -> None
        if isinstance(request, Put) and request.path[1] == "design":
            # We have hooked self.reload to PreConfigure, and reload() will
            # set design attribute, so explicitly allow this without checking
            # it is in no_save (as it won't be in there)
            pass
        else:
            super(DetectorChildPart, self).notify_dispatch_request(request)

    @add_call_types
    def reset(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        if child.abort.meta.writeable:
            child.abort()
        super(DetectorChildPart, self).reset(context)

    # Must match those passed in configure() Method, so need to be camelCase
    # noinspection PyPep8Naming
    @add_call_types
    def validate(self,
                 context,  # type: AContext
                 part_info,  # type: APartInfo
                 generator,  # type: AGenerator
                 fileDir,  # type: AFileDir
                 detectors=None,  # type: ADetectorTable
                 axesToMove=None,  # type: AAxesToMove
                 fileTemplate="%s.h5",  # type: AFileTemplate
                 ):
        # type: (...) -> UParameterTweakInfos
        # Work out if we are taking part
        frames_per_step, kwargs = self._configure_args(
            generator, fileDir, detectors, axesToMove, fileTemplate)
        if frames_per_step < 1:
            # We aren't
            return
        if frames_per_step > 1:
            # Check something else is multiplying out triggers
            infos = [i for i in DetectorMutiframeInfo.filter_values(part_info)
                     if i.mri == self.mri]
            assert infos, \
                "There are no trigger multipliers setup for Detector '%s' " \
                "so framesPerStep can only be 0 or 1 for this row in the " \
                "detectors table" % self.name
        child = context.block_view(self.mri)
        # This is a Serializable with the correct entries
        try:
            returns = child.validate(**kwargs)
        except Exception as e:
            raise BadValueError("Validate of %s failed: %s" % (
                self.mri, stringify_error(e)))
        # TODO: this will fail if we split across 2 Malcolm processes as
        # scanpointgenerators don't compare equal, but we don't want to
        # serialize everything as that is expensive for arrays
        ret = []
        for k in returns:
            v = returns[k]
            if kwargs.get(k, v) != v:
                ret.append(ParameterTweakInfo(k, v))
        return ret

    def _configure_args(self,
                        generator,  # type: AGenerator
                        file_dir,  # type: AFileDir
                        detectors=None,  # type: ADetectorTable
                        axes_to_move=None,  # type: AAxesToMove
                        file_template="%s.h5",  # type: AFileTemplate
                        ):
        # type: (...) -> Tuple[int, Dict[str, Any]]
        # Check the detector table to see what we need to do
        for name, mri, exposure, frames in detectors.rows():
            if name == self.name and frames > 0:
                # Found a row saying to take part
                assert mri == self.mri, \
                    "%s has mri %s, passed %s" % (name, self.mri, mri)
                break
        else:
            # Didn't find a row or no frames, don't take part
            return 0, {}
        # If we had more than one frame per point, multiply out
        if frames > 1:
            axis_name = name + "_frames_per_step"
            axes_to_move = list(axes_to_move) + [axis_name]
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
            generator = CompoundGenerator.from_dict(serialized)
        kwargs = dict(
            generator=generator,
            axesToMove=axes_to_move,
            fileDir=file_dir,
            # formatName is the unique part of the HDF filename, so use the part
            # name for this
            formatName=self.name,
            fileTemplate=file_template
        )
        if exposure > 0.0:
            kwargs["exposure"] = exposure
        return frames, kwargs

    # Must match those passed in configure() Method, so need to be camelCase
    # noinspection PyPep8Naming
    @add_call_types
    def configure(self,
                  context,  # type: AContext
                  generator,  # type: AGenerator
                  fileDir,  # type: AFileDir
                  detectors=None,  # type: ADetectorTable
                  axesToMove=None,  # type: AAxesToMove
                  fileTemplate="%s.h5",  # type: AFileTemplate
                  ):
        # type: (...) -> UInfos
        # Work out if we are taking part
        self.frames_per_step, kwargs = self._configure_args(
            generator, fileDir, detectors, axesToMove, fileTemplate)
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        child = context.block_view(self.mri)
        child.configure(**kwargs)
        # Report back any datasets the child has to our parent
        assert hasattr(child, "datasets"), \
            "Detector %s doesn't have a dataset table, did you add a " \
            "DatasetTablePart to it?" % self.mri
        datasets_table = child.datasets.value
        info_list = [DatasetProducedInfo(*row) for
                     row in datasets_table.rows()]
        return info_list

    @add_call_types
    def run(self, context):
        # type: (AContext) -> None
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.completedSteps.subscribe_value(self.update_completed_steps)
        bad_states = [ss.DISABLING, ss.ABORTING, ss.FAULT]
        match_future = child.when_value_matches_async(
            "state", ss.POSTRUN, bad_states)
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
                raise self.run_future.exception()
            else:
                raise

    @add_call_types
    def post_run(self, context):
        # type: (AContext) -> None
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        context.wait_all_futures(self.run_future)

    @add_call_types
    def seek(self, context, completed_steps):
        # type: (AContext, ACompletedSteps) -> None
        if self.frames_per_step < 1:
            # We aren't taking part in the scan
            return
        # Clear out the update_completed_steps and match_future subscriptions
        context.unsubscribe_all()
        child = context.block_view(self.mri)
        child.pause(lastGoodStep=completed_steps)

    @add_call_types
    def abort(self, context):
        # type: (AContext) -> None
        child = context.block_view(self.mri)
        child.abort()

    def update_completed_steps(self, value):
        # type: (int) -> None
        self.registrar.report(RunProgressInfo(value // self.frames_per_step))
