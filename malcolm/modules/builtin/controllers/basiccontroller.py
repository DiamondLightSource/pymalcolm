from typing import Dict, Optional

from malcolm.core import ADescription, Alarm, AMri, Controller, StringMeta, Widget

from ..infos import HealthInfo, LabelInfo

# Pull re-used annotypes into our namespace in case we are subclassed
AMri = AMri
ADescription = ADescription


class BasicController(Controller):
    """Basic Controller with Health and Title updating"""

    def __init__(self, mri: AMri, description: ADescription = "") -> None:
        super().__init__(mri, description)
        self._faults: Dict[object, Alarm] = {}
        self.info_registry.add_reportable(LabelInfo, self.update_label)
        self.info_registry.add_reportable(HealthInfo, self.update_health)
        self.health = StringMeta(
            "Displays OK or an error message", tags=[Widget.TEXTUPDATE.tag()]
        ).create_attribute_model("OK")
        self.field_registry.add_attribute_model("health", self.health)

    def update_label(self, _: object, info: LabelInfo) -> None:
        """Set the label of the Block Meta object"""
        with self._lock:
            self._block.meta.set_label(info.label)

    def update_health(self, reporter: object, info: HealthInfo) -> None:
        """Set the health attribute. Called from part"""
        with self.changes_squashed:
            alarm = info.alarm
            ts = info.ts
            if alarm.is_ok():
                self._faults.pop(reporter, None)
            else:
                self._faults[reporter] = alarm
            alarm_to_set: Optional[Alarm]
            if self._faults:
                # Sort them by severity
                faults = sorted(self._faults.values(), key=lambda a: a.severity.value)
                alarm_to_set = faults[-1]
                text = faults[-1].message
            else:
                alarm_to_set = None
                text = "OK"
            self.health.set_value(text, alarm=alarm_to_set, ts=ts)
