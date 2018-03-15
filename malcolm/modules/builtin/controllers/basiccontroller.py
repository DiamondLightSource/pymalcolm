from malcolm.core import Controller, StringMeta, AMri, ADescription, \
    AUseCothread, Widget
from ..infos import TitleInfo, HealthInfo


class BasicController(Controller):
    """Basic Controller with Health and Title updating"""
    def __init__(self, mri, description="", use_cothread=True):
        # type: (AMri, ADescription, AUseCothread) -> None
        super(BasicController, self).__init__(mri, description, use_cothread)
        self._faults = {}  # Dict[Part, Alarm]
        self.info_registry.add_reportable(TitleInfo, self.update_title)
        self.info_registry.add_reportable(HealthInfo, self.update_health)
        self.health = StringMeta(
            "Displays OK or an error message", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model("OK")
        self.field_registry.add_attribute_model("health", self.health)

    def update_title(self, _, info):
        # type: (object, TitleInfo) -> None
        """Set the label of the Block Meta object"""
        with self._lock:
            self._block.meta.set_label(info.title)

    def update_health(self, reporter, info):
        # type: (object, HealthInfo) -> None
        """Set the health attribute. Called from part"""
        with self.changes_squashed:
            alarm = info.alarm
            if alarm.is_ok():
                self._faults.pop(reporter, None)
            else:
                self._faults[reporter] = alarm
            if self._faults:
                # Sort them by severity
                faults = sorted(self._faults.values(),
                                key=lambda a: a.severity.value)
                alarm = faults[-1]
                text = faults[-1].message
            else:
                alarm = None
                text = "OK"
            self.health.set_value(text, alarm=alarm)
