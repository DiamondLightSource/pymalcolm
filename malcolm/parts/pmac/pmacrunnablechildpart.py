from malcolm.controllers.runnablecontroller import RunnableController
from malcolm.parts.builtin.runnablechildpart import RunnableChildPart


class PmacRunnableChildPart(RunnableChildPart):

    @RunnableController.Pause
    def pause(self, task):
        task.post(self.child["pause"])
