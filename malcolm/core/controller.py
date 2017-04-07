from contextlib import contextmanager
import inspect
import weakref

from malcolm.compat import OrderedDict
from .alarm import Alarm
from .attribute import Attribute
from .attributemodel import AttributeModel
from .block import Block
from .blockmeta import BlockMeta
from .blockmodel import BlockModel
from .context import Context
from .errors import UnexpectedError, AbortedError
from .healthmeta import HealthMeta
from .hook import Hook, get_hook_decorated
from .loggable import Loggable
from .map import Map
from .method import Method
from .methodmodel import MethodModel, get_method_decorated
from .model import Model
from .notifier import Notifier
from .request import Get, Subscribe, Unsubscribe, Put, Post
from .queue import Queue
from .rlock import RLock
from .serializable import serialize_object, deserialize_object
from .view import make_view


class Controller(Loggable):
    use_cothread = True

    # Attributes
    health = None

    def __init__(self, process, mri, parts):
        self.set_logger_name("%s(%s)" % (type(self).__name__, mri))
        self.process = process
        self.mri = mri
        self._request_queue = Queue()
        # {Part: fault string}
        self._faults = {}
        # {Hook: name}
        self._hook_names = self._find_hooks()
        # {name: Part}
        self.parts = self._setup_parts(parts)
        # {part_name: (field_name, Model, setter)
        self.part_fields = {}
        self._lock = RLock(self.use_cothread)
        self._block = BlockModel()
        self._notifier = Notifier(mri, self._lock, self._block)
        self._block.set_notifier_path(self._notifier, [mri])
        self._write_functions = {}
        self._add_block_fields()

    def _setup_parts(self, parts):
        parts_dict = OrderedDict()
        for part in parts:
            part.attach_to_controller(self)
            # Check part hooks into one of our hooks
            for func_name, part_hook, _ in get_hook_decorated(part):
                assert part_hook in self._hook_names, \
                    "Part %s func %s not hooked into %s" % (
                        part.name, func_name, self)
            parts_dict[part.name] = part
        return parts_dict

    def _find_hooks(self):
        hook_names = {}
        for name, member in inspect.getmembers(self, Hook.isinstance):
            assert member not in hook_names, \
                "Hook %s already in %s as %s" % (self, name, hook_names[member])
            hook_names[member] = name
        return hook_names

    def _add_block_fields(self):
        for iterable in ([self.create_meta()], self.create_attributes(),
                         self.create_methods(), self.create_part_fields()):
            for name, child, writeable_func in iterable:
                self.add_block_field(name, child, writeable_func)

    def add_block_field(self, name, child, writeable_func):
        self._block.set_endpoint_data(name, child)
        if writeable_func:
            self._write_functions[name] = writeable_func
            if isinstance(child, AttributeModel):
                child.meta.set_writeable(True)
            elif isinstance(child, MethodModel):
                child.set_writeable(True)
                for k, v in child.takes.elements.items():
                    v.set_writeable(True)

    def create_methods(self):
        """Method that should provide Method instances for Block

        Yields:
            tuple: (string name, Method, callable post_function).
        """
        return get_method_decorated(self)

    def create_attributes(self):
        """MethodModel that should provide Attribute instances for Block

        Yields:
            tuple: (string name, Attribute, callable put_function).
        """
        self.health = HealthMeta().create_attribute()
        yield "health", self.health, None

    def create_meta(self):
        """Create the Block meta object"""
        return "meta", BlockMeta(), None

    def create_part_fields(self):
        for name, part in self.parts.items():
            part_fields = list(part.create_attributes()) + \
                          list(part.create_methods())
            self.part_fields[name] = part_fields
            for data in part_fields:
                yield data

    def spawn(self, func, *args, **kwargs):
        """Spawn a function in the right thread"""
        spawned = self.process.spawn(func, args, kwargs, self.use_cothread)
        return spawned

    @property
    @contextmanager
    def lock_released(self):
        self._lock.release()
        try:
            yield
        finally:
            self._lock.acquire()

    @property
    def changes_squashed(self):
        return self._notifier.changes_squashed

    def set_health(self, part, alarm=None):
        """Set the health attribute"""
        if alarm is not None:
            alarm = deserialize_object(alarm, Alarm)
        with self.changes_squashed:
            if alarm is None:
                self._faults.pop(part, None)
            else:
                self._faults[part] = alarm
            if self._faults:
                # Sort them by severity
                faults = sorted(self._faults.values(), key=lambda a: a.severity)
                alarm = faults[-1]
                text = faults[-1].message
            else:
                alarm = None
                text = "OK"
            self.health.set_value(text)
            self.health.set_alarm(alarm)
            self.health.set_timeStamp()

    def block_view(self):
        """Get a view of the block we control

        Returns:
            Block: The block we control
        """
        context = Context("Context", self.process)
        return self.make_view(context)

    def make_view(self, context, data=None, child_name=None):
        """Make a child View of data[child_name]"""
        with self._lock:
            if data is None:
                child = self._block
            else:
                child = data[child_name]
            child_view = self._make_view(context, child)
        return child_view

    def _make_view(self, context, data):
        if isinstance(data, BlockModel):
            # Make an Attribute View
            return make_view(self, context, data, Block)
        elif isinstance(data, AttributeModel):
            # Make an Attribute View
            return make_view(self, context, data, Attribute)
        elif isinstance(data, MethodModel):
            # Make a Method View
            return make_view(self, context, data, Method)
        elif isinstance(data, Model):
            # Make a view of it
            return make_view(self, context, data)
        elif isinstance(data, dict):
            # Need to recurse down
            d = OrderedDict()
            for k, v in data.items():
                d[k] = self._make_view(context, v)
            return d
        elif isinstance(data, list):
            # Need to recurse down
            return [self._make_view(context, x) for x in data]
        else:
            return data

    def handle_request(self, request):
        """Spawn a new thread that handles Request"""
        self._request_queue.put(request)
        return self.spawn(self._handle_request)

    def _handle_request(self):
        responses = []
        with self._lock:
            request = self._request_queue.get(timeout=0)
            if isinstance(request, Get):
                handler = self._handle_get
            elif isinstance(request, Put):
                handler = self._handle_put
            elif isinstance(request, Post):
                handler = self._handle_post
            elif isinstance(request, Subscribe):
                handler = self._notifier.handle_subscribe
            elif isinstance(request, Unsubscribe):
                handler = self._notifier.handle_unsubscribe
            else:
                raise UnexpectedError("Unexpected request %s", request)
            try:
                responses += handler(request)
            except Exception as e:
                responses.append(request.error_response(e))
        for cb, response in responses:
            try:
                cb(response)
            except Exception as e:
                self.log_exception("Exception notifying %s", response)

    def _handle_get(self, request):
        """Called with the lock taken"""
        data = self._block
        for endpoint in request.path[1:]:
            data = data[endpoint]
        serialized = serialize_object(data)
        ret = [request.return_response(serialized)]
        return ret

    def _handle_put(self, request):
        """Called with the lock taken"""
        attribute_name = request.path[1]

        attribute = self._block[attribute_name]
        assert attribute.meta.writeable, \
            "Attribute %s is not writeable" % attribute_name
        put_function = self._write_functions[attribute_name]

        with self.lock_released:
            result = put_function(request.value)

        ret = [request.return_response(result)]
        return ret

    def _handle_post(self, request):
        """Called with the lock taken"""
        method_name = request.path[1]
        if request.parameters:
            param_dict = request.parameters
        else:
            param_dict = {}

        method = self._block[method_name]
        assert method.writeable, \
            "Method %s is not writeable" % method_name
        args = method.prepare_call_args(**param_dict)
        post_function = self._write_functions[method_name]

        with self.lock_released:
            result = post_function(*args)

        result = self.validate_result(method_name, result)
        ret = [request.return_response(result)]
        return ret

    def validate_result(self, method_name, result):
        with self._lock:
            method = self._block[method_name]
            # Prepare output map
            if method.returns.elements:
                result = Map(method.returns, result)
                result.check_valid()
        return result

    def create_part_contexts(self):
        part_contexts = {}
        for part_name, part in self.parts.items():
            part_contexts[part] = Context(
                "Context(%s)" % part_name, self.process)
        return part_contexts

    def run_hook(self, hook, part_contexts, *args, **params):
        hook_queue, hook_runners = self.start_hook(
            hook, part_contexts, *args, **params)
        return_dict = self.wait_hook(hook_queue, hook_runners)
        return return_dict

    def start_hook(self, hook, part_contexts, *args, **params):
        assert hook in self._hook_names, \
            "Hook %s doesn't appear in _controller hooks %s" % (
                hook, self._hook_names)

        # This queue will hold (part, result) tuples
        hook_queue = Queue()

        # ask the hook to find the functions it should run
        part_funcs = hook.find_hooked_functions(self.parts.values())
        hook_runners = {}

        # now start them off
        for part, func_name in part_funcs.items():
            context = part_contexts[part]
            hook_runners[part] = part.make_hook_runner(
                hook_queue, func_name, weakref.proxy(context), *args, **params)

        return hook_queue, hook_runners

    def wait_hook(self, hook_queue, hook_runners):
        # Wait for them all to finish
        return_dict = {}
        while hook_runners:
            part, ret = hook_queue.get()
            hook_runner = hook_runners.pop(part)

            if isinstance(ret, AbortedError):
                # If AbortedError, all tasks have already been stopped.
                # Do not wait on them otherwise we might get a deadlock...
                raise ret

            # Wait for the process to terminate
            hook_runner.wait()
            return_dict[part.name] = ret
            self.log_debug("Part %s returned %r. Still waiting for %s",
                           part.name, ret, [p.name for p in hook_runners])

            if isinstance(ret, Exception):
                # Got an error, so stop and wait all hook runners
                for h in hook_runners.values():
                    h.stop()
                # Wait for them to finish
                for h in hook_runners.values():
                    h.wait()
                raise ret

        return return_dict
