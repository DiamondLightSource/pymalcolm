from annotypes import Anno

from malcolm.modules.ca.parts.cachoicepart import CAChoicePart
import malcolm.modules.ca.util as util
from malcolm.core import PartRegistrar, DEFAULT_TIMEOUT
from .. import hooks

with Anno("Value used to open shutter"):
    AOpenVal = str

with Anno("Value used to close shutter"):
    ACloseVal = str

with Anno("Whether to open shutter during run or configure"):
    AOpenDurRun = bool


class ShutterPart(CAChoicePart):

    def __init__(self,
                 name,  # type: util.APartName
                 description,  # type: util.AMetaDescription
                 open_value,  # type: AOpenVal
                 close_value,  # type: ACloseVal
                 pv="",  # type: util.APv
                 rbv="",  # type: util.ARbv
                 rbv_suffix="",  # type: util.ARbvSuffix
                 open_during_run=False,  # type: AOpenDurRun
                 min_delta=0.05,  # type: util.AMinDelta
                 timeout=DEFAULT_TIMEOUT,  # type: util.ATimeout
                 sink_port=None,  # type: util.ASinkPort
                 widget=None,  # type: util.AWidget
                 group=None,  # type: util.AGroup
                 config=True  # type: util.AConfig
                 ):
        # type: (...) -> None
        super(ShutterPart, self).__init__(name, description, pv, rbv, rbv_suffix, min_delta, timeout, sink_port,
                                          widget, group, config)

        self.open_value = open_value
        self.close_value = close_value
        self.open_during_run = open_during_run

    def setup(self, registrar):
        # type: (PartRegistrar) -> None
        super(ShutterPart, self).setup(registrar)
        # Hooks
        if self.open_during_run:
            registrar.hook(hooks.RunHook, self.open_shutter)
        else:
            registrar.hook(hooks.ConfigureHook, self.open_shutter)
        registrar.hook(hooks.ResumeHook, self.open_shutter)
        registrar.hook(hooks.PauseHook, self.close_shutter)
        registrar.hook(hooks.AbortHook, self.close_shutter)
        registrar.hook(hooks.PostRunReadyHook, self.close_shutter)

    def open_shutter(self):
        self.caput(self.open_value)

    def close_shutter(self):
        self.caput(self.close_value)
