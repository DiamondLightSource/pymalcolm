import inspect


class Hook(object):
    def __call__(self, func):
        """Decorator function to add a Hook to a Part's function

        Args:
            func: Function to decorate with Hook

        Returns:
            Decorated function
        """

        if not hasattr(func, "Hooked"):
            func.Hooked = []
        func.Hooked.append(self)
        return func

    @classmethod
    def isinstance(cls, o):
        return isinstance(o, cls)


def get_hook_decorated(part):
    for name, member in inspect.getmembers(part, inspect.ismethod):
        if hasattr(member, "Hooked"):
            for hook in member.Hooked:
                yield name, hook, member
