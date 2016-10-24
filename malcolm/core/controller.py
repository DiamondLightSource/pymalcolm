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


@method_takes()
class Controller(Loggable):
    """Implement the logic that takes a Block through its state machine"""
    stateMachine = sm()

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
        # {state (str): {Meta/MethodMeta/Attribute: writeable (bool)}
        self.children_writeable = {}
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
        child_list += list(self.create_attributes())
        child_list += list(self.create_methods())
        for part in self.parts.values():
            child_list += list(part.create_attributes())
            child_list += list(part.create_methods())

        self.children_writeable = {}
        writeable_functions = {}
        children = OrderedDict()

        for name, child, writeable_func in child_list:
            if isinstance(child, Attribute):
                states = child.meta.writeable_in
            else:
                states = child.writeable_in
            children[name] = child
            if states:
                for state in states:
                    assert state in self.stateMachine.possible_states, \
                        "State %s is not one of the valid states %s" % \
                        (state, self.stateMachine.possible_states)
            elif writeable_func is not None:
                states = [
                    state for state in self.stateMachine.possible_states
                    if state not in (sm.DISABLING, sm.DISABLED)]
            else:
                continue
            self.register_child_writeable(name, states)
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

    def create_meta(self):
        self.meta = BlockMeta()
        return "meta", self.meta, None

    def create_attributes(self):
        """Method that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        # Add the state, status and busy attributes
        self.state = ChoiceMeta(
            "State of Block", self.stateMachine.possible_states, label="State"
        ).make_attribute()
        yield "state", self.state, None
        self.status = StringMeta(
            "Status of Block", label="Status"
        ).make_attribute()
        yield "status", self.status, None
        self.busy = BooleanMeta(
            "Whether Block busy or not", label="Busy"
        ).make_attribute()
        yield "busy", self.busy, None

    def create_methods(self):
        """Method that should provide MethodMeta instances for Block

        Yields:
            tuple: (string name, MethodMeta, callable post_function).
        """
        return get_method_decorated(self)

    def transition(self, state, message):
        """
        Change to a new state if the transition is allowed

        Args:
            state(str): State to transition to
            message(str): Status message
        """
        with self.lock:
            if self.stateMachine.is_allowed(
                    initial_state=self.state.value, target_state=state):
                self._do_transition(state, message)
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

        # say which children are now writeable
        for name in self.block:
            try:
                writeable = self.children_writeable[state][name]
            except KeyError:
                continue
            child = self.block[name]
            if isinstance(child, Attribute):
                child = child.meta
            elif isinstance(child, MethodMeta):
                for ename in child.takes.elements:
                    meta = child.takes.elements[ename]
                    self.add_change(changes, meta, "writeable", writeable)
            try:
                self.add_change(changes, child, "writeable", writeable)
            except ValueError:
                self.log_exception("%s %s", name, child)
                raise

        self.log_debug("Transitioning to %s", state)
        self.block.apply_changes(*changes)

    def register_child_writeable(self, name, states):
        """
        Set the states that the given method can be called in

        Args:
            name (str): Child name that will be set writeable or not
            states (list[str]): List of states where method is writeable
        """
        for state in self.stateMachine.possible_states:
            writeable_dict = self.children_writeable.setdefault(state, {})
            is_writeable = state in states
            writeable_dict[name] = is_writeable

    def create_part_tasks(self):
        part_tasks = {}
        for part_name, part in self.parts.items():
            part_tasks[part] = Task("Task(%s)" % part_name, self.process)
        return part_tasks

    def run_hook(self, hook, part_tasks, *args, **params):
        hook_queue, task_part_names = self.start_hook(
            hook, part_tasks, *args, **params)
        return_dict = self.wait_hook(hook_queue, task_part_names)
        return return_dict

    def make_task_return_value_function(self, hook_queue, *args, **params):

        def task_return(func, method_meta, task):
            filtered_params = {}
            if method_meta is None:
                method_meta = MethodMeta()
                method_meta.set_logger_name("MethodMeta")
            for k, v in params.items():
                if k in method_meta.takes.elements:
                    filtered_params[k] = v
            try:
                result = method_meta.call_post_function(
                    func, filtered_params, task, *args)
            except StopIteration as e:
                self.log_error("%s has been aborted", func)
                result = e
            except Exception as e:  # pylint:disable=broad-except
                self.log_exception("%s %s raised exception", func, params)
                result = e
            self.log_debug("Putting %r on queue", result)
            hook_queue.put((task, result))

        return task_return

    def start_hook(self, hook, part_tasks, *args, **params):
        assert hook in self.hook_names, \
            "Hook %s doesn't appear in controller hooks %s" % (
                hook, self.hook_names)
        self.log_debug("Run %s hook", self.hook_names[hook])

        # ask the hook to find the functions it should run
        part_funcs = hook.find_hooked_functions(self.parts)

        # now start them off
        task_part_names = {}
        hook_queue = self.process.create_queue()
        for part_name, func_name in part_funcs.items():
            part = self.parts[part_name]
            func = getattr(part, func_name)
            method_meta = part.method_metas.get(func_name, None)
            task_return = self.make_task_return_value_function(
                hook_queue, *args, **params)
            task = part_tasks[part]
            task_part_names[task] = part_name
            task.define_spawn_function(task_return, func, method_meta, task)
            self.log_error("Starting part %s task %r", part_name, task)
            task.start()

        return hook_queue, task_part_names

    def wait_hook(self, hook_queue, task_part_names):
        # Wait for them all to finish
        return_dict = {}
        while task_part_names:
            self.log_error("Waiting for %s" % (task_part_names,))
            task, ret = hook_queue.get()
            self.log_error("Got %s %s" % (task, ret))
            part_name = task_part_names.pop(task)
            return_dict[part_name] = ret
            self.log_error("Part %s returned %s" % (part_name, ret))

            if isinstance(ret, Exception):
                # Stop all other tasks
                for task in task_part_names:
                    task.stop()
                for task in task_part_names:
                    task.wait()

            # If we got a StopIteration, someone asked us to stop, so
            # don't wait, otherwise make sure we finished
            if not isinstance(ret, StopIteration):
                task.wait()

            if isinstance(ret, Exception):
                raise ret

        return return_dict
