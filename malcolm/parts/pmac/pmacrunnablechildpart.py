from malcolm.controllers.scanning.runnablecontroller import RunnableController
from malcolm.parts.scanpointgenerator.runnablechildpart import RunnableChildPart


class PmacRunnableChildPart(RunnableChildPart):

    @RunnableController.Pause
    def pause(self, task):
        task.post(self.child["pause"])
