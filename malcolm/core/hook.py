import inspect

from malcolm.core.loggable import Loggable
# from malcolm.core.task import Task


class Task(object):

    def __init__(self, process):
        self.process = process


class Hook(Loggable):

    def __call__(self, func):
        func.hook = self
        return func

    def run(self, controller):

        names = [n for n in dir(controller) if getattr(controller, n) is self]
        assert len(names) > 0, \
            "Hook is not in controller"
        assert len(names) == 1, \
            "Hook appears in controller multiple times as %s" % names

        self.set_logger_name("%s.%s" % (controller.block.name, names[0]))

        active_tasks = []
        for part in controller.parts:
            members = [value[1] for value in
                       inspect.getmembers(part, predicate=inspect.ismethod)]

            for function in members:
                if hasattr(function, "hook") and function.hook == self:
                    task_queue = controller.process.create_queue()
                    task = Task(controller.process)
                    task_queue.put(controller.process.spawn(
                        self._run_func, controller.process.q, function, task))

                    active_tasks.append(task)

        while active_tasks:
            response = controller.process.q.get()
            active_tasks.pop(0)

            if isinstance(response, Exception):
                for task in active_tasks:
                    task.stop()
                raise response

        return

    @staticmethod
    def _run_func(q, func, task):
        try:
            result = func(task)
        except Exception as e:
            q.put(e)
        else:
            q.put(result)

