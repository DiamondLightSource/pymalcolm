from malcolm.core import method_takes
from malcolm.modules.builtin.parts import StatefulChildPart
from malcolm.modules.builtin.vmetas import StringMeta
from malcolm.modules.scanning.controllers import RunnableController

class ExcaliburFileMungePart(StatefulChildPart):
   @RunnableController.Configure
   @method_takes(
        "formatName", StringMeta(
            "Argument for fileTemplate, normally filename without extension"),
        "det")
   def configure(self, context, completed_steps, steps_to_do, part_info, params):
        pass
