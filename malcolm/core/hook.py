import inspect

from malcolm.core.task import Task


class Hook(object):

    def __call__(self, func):
        """
        Decorator function to add a Hook to a Part's function

        Args:
            func: Function to decorate with Hook

        Returns:
            Decorated function
        """

        func.Hook = self
        return func

    @staticmethod
    def _run_func(q, func, task):
        """
        Run a function and place the response or exception back on the queue

        Args:
            q(Queue): Queue to place response/exception raised on
            func: Function to run
            task(Task): Task to run function with
        """

        try:
            result = func(task)
        except Exception as e:  # pylint:disable=broad-except
            q.put((task, e))
        else:
            q.put((task, result))

def get_decorated_functions(part):
    for name, member in inspect.getmembers(part, inspect.ismethod):
        if hasattr(member, "Hook"):
            yield name, member.Hook, member
