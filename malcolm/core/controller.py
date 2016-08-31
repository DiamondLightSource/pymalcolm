import functools
from collections import OrderedDict

from malcolm.core.attribute import Attribute
from malcolm.core.block import Block
from malcolm.core.blockmeta import BlockMeta
from malcolm.core.hook import Hook, get_hook_decorated
from malcolm.core.loggable import Loggable
from malcolm.core.methodmeta import method_takes, MethodMeta, \
    get_method_decorated
from malcolm.core.request import Post
from malcolm.core.statemachine import DefaultStateMachine
from malcolm.core.task import Task
from malcolm.core.vmetas import BooleanMeta, ChoiceMeta, StringMeta


sm = DefaultStateMachine


@sm.insert
@method_takes()
class Controller(Loggable):
    """Implement the logic that takes a Block through its state machine"""

    # Attributes for all controllers
    state = None
    status = None
    busy = None
    # BlockMeta for descriptions
    meta = None

    def __init__(self, block_name, process, parts=None, params=None):
        """
        Args:
            process (Process): The process this should run under
        """
        controller_name = "%s(%s)" % (type(self).__name__, block_name)
        self.set_logger_name(controller_name)
        self.block = Block()
        self.log_debug("Creating block %r as %r" % (self.block, block_name))
        self.block_name = block_name
        self.params = params
        self.process = process
        self.lock = process.create_lock()
        # {part: task}
        self.part_tasks = {}
        # dictionary of dictionaries
        # {state (str): {MethodMeta: writeable (bool)}
        self.methods_writeable = {}
        # dict {hook: name}
        self.hook_names = self._find_hooks()
        self.parts = self._setup_parts(parts, controller_name)
        self._set_block_children()
        self._do_transition(sm.DISABLED, "Disabled")
        self.block.set_parent(process, block_name)
        process.add_block(self.block)
        self.do_initial_reset()

    def _find_hooks(self):
        hook_names = {}
        for n in dir(self):
            attr = getattr(self, n)
            if isinstance(attr, Hook):
                assert attr not in hook_names, \
                    "Hook %s already in controller as %s" % (
                        n, hook_names[attr])
                hook_names[attr] = n
        return hook_names

    def _setup_parts(self, parts, controller_name):
        if parts is None:
            parts = {}
        for part_name, part in parts.items():
            part.set_logger_name("%s.%s" % (controller_name, part_name))
            # Check part hooks into one of our hooks
            for func_name, part_hook, _ in get_hook_decorated(part):
                assert part_hook in self.hook_names, \
                    "Part %s func %s not hooked into %s" % (
                        part, func_name, self)
        return parts

    def do_initial_reset(self):
        request = Post(
            None, self.process.create_queue(), [self.block_name, "reset"])
        self.process.q.put(request)

    def add_change(self, changes, item, attr, value):
        path = item.path_relative_to(self.block) + [attr]
        changes.append([path, value])

    def _set_block_children(self):
        # reconfigure block with new children
        child_list = [self.create_meta()]
        child_list += list(self._create_default_attributes())
        child_list += list(self.create_attributes())
        child_list += list(self.create_methods())
        for part in self.parts.values():
            child_list += list(part.create_attributes())
            child_list += list(part.create_methods())

        self.methods_writeable = {}
        writeable_functions = {}
        children = OrderedDict()

        for name, child, writeable_func in child_list:
            if isinstance(child, MethodMeta):
                # Set if the method is writeable
                if child.only_in is None:
                    states = [
                        state for state in self.stateMachine.possible_states
                        if state not in (sm.DISABLING, sm.DISABLED)]
                else:
                    states = child.only_in
                    for state in states:
                        assert state in self.stateMachine.possible_states, \
                            "State %s is not one of the valid states %s" % \
                            (state, self.stateMachine.possible_states)
                # Make a copy otherwise all instances will own the same one
                child = MethodMeta.from_dict(child.to_dict())
                self.register_method_writeable(child, states)
            elif isinstance(child, Attribute):
                child.meta.set_writeable(writeable_func is not None)
            children[name] = child
            if writeable_func:
                writeable_functions[name] = functools.partial(
                    self.call_writeable_function, writeable_func)

        self.block.replace_endpoints(children)
        self.block.set_writeable_functions(writeable_functions)

    def call_writeable_function(self, function, child, *args):
        with self.lock:
            if not child.writeable:
                child.log_error("I'm not writeable")
                raise ValueError("Child %r is not writeable" % (child,))
        result = function(*args)
        return result

    def _create_default_attributes(self):
        # Add the state, status and busy attributes
        self.state = Attribute(
            ChoiceMeta("State of Block", self.stateMachine.possible_states))
        yield ("state", self.state, None)
        self.status = Attribute(StringMeta("Status of Block"))
        yield ("status", self.status, None)
        self.busy = Attribute(BooleanMeta("Whether Block busy or not"))
        yield ("busy", self.busy, None)

    def create_meta(self):
        self.meta = BlockMeta()
        return "meta", self.meta, None

    def create_attributes(self):
        """Method that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        return iter(())

    def create_methods(self):
        """Method that should provide MethodMeta instances for Block

        Yields:
            tuple: (string name, MethodMeta, callable post_function).
        """
        return get_method_decorated(self)

    def transition(self, state, message, create_tasks=False):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
            create_tasks(bool): If true then make self.part_tasks
        """
        with self.lock:
            if self.stateMachine.is_allowed(
                    initial_state=self.state.value, target_state=state):
                self._do_transition(state, message)
                if create_tasks:
                    self.part_tasks = self.create_part_tasks()
            else:
                raise TypeError("Cannot transition from %s to %s" %
                                (self.state.value, state))

    def _do_transition(self, state, message):
        # transition is allowed, so set attributes
        changes = []
        self.add_change(changes, self.state, "value", state)
        self.add_change(changes, self.status, "value", message)
        self.add_change(changes, self.busy, "value",
                        state in self.stateMachine.busy_states)

        # say which methods can now be called
        for name in self.block:
            child = self.block[name]
            if isinstance(child, MethodMeta):
                method = child
                writeable = self.methods_writeable[state][method]
                self.log_debug("Setting %s %s to writeable %s", name, method, writeable)
                self.add_change(changes, method, "writeable", writeable)
                for ename in method.takes.elements:
                    meta = method.takes.elements[ename]
                    self.add_change(changes, meta, "writeable", writeable)

        self.block.apply_changes(*changes)

    def register_method_writeable(self, method, states):
        """
        Set the states that the given method can be called in

        Args:
            method(MethodMeta): Method that will be set writeable or not
            states(list[str]): List of states where method is writeable
        """
        for state in self.stateMachine.possible_states:
            writeable_dict = self.methods_writeable.setdefault(state, {})
            is_writeable = state in states
            writeable_dict[method] = is_writeable

    def create_part_tasks(self):
        part_tasks = {}
        for part_name, part in self.parts.items():
            part_tasks[part] = Task("Task(%s)" % part_name, self.process)
        return part_tasks

    def run_hook(self, hook, part_tasks, **kwargs):
        hook_queue, func_tasks, task_part_names = self.start_hook(
            hook, part_tasks, **kwargs)
        return self.wait_hook(hook_queue, func_tasks, task_part_names)

    def start_hook(self, hook, part_tasks, **kwargs):
        assert hook in self.hook_names, \
            "Hook %s doesn't appear in controller hooks %s" % (
                hook, self.hook_names)
        self.log_debug("Running %s hook", self.hook_names[hook])

        # ask the hook to find the functions it should run
        func_tasks = hook.find_func_tasks(part_tasks)

        # now start them off
        hook_queue = self.process.create_queue()

        def _gather_task_return_value(func, task):
            try:
                result = func.MethodMeta.call_post_function(func, kwargs, task)
            except Exception as e:  # pylint:disable=broad-except
                self.log_exception("%s %s raised exception", func, kwargs)
                hook_queue.put((func, e))
            else:
                hook_queue.put((func, result))

        for func, task in func_tasks.items():
            task.define_spawn_function(_gather_task_return_value, func, task)
            task.start()

        # Create the reverse dictionary so we know where to store the results
        task_part_names = {}
        for part_name, part in self.parts.items():
            if part in part_tasks:
                task_part_names[part_tasks[part]] = part_name

        return hook_queue, func_tasks, task_part_names

    def wait_hook(self, hook_queue, func_tasks, task_part_names):
        # Wait for them all to finish
        return_dict = {}
        while func_tasks:
            func, ret = hook_queue.get()
            task = func_tasks.pop(func)
            # Need to wait on it to clear spawned
            task.wait()
            part_name = task_part_names[task]
            return_dict[part_name] = ret
            if isinstance(ret, Exception):
                # Stop all other tasks
                for task in func_tasks.values():
                    task.stop()
                for task in func_tasks.values():
                    task.wait()
                raise ret

        return return_dict
