from contextlib import contextmanager
import inspect
import weakref
import time

from malcolm.compat import OrderedDict
from .alarm import Alarm
from .attribute import Attribute
from .attributemodel import AttributeModel
from .block import Block, make_block_view
from .blockmodel import BlockModel
from .context import Context
from .errors import UnexpectedError, AbortedError, WrongThreadError
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
from .serializable import serialize_object, deserialize_object, camel_to_title
from .view import make_view


ABORT_TIMEOUT = 5.0


class Controller(Loggable):
    use_cothread = True

    # Attributes
    health = None

    def __init__(self, process, mri, parts, description=""):
        super(Controller, self).__init__(mri=mri)
        self.process = process
        self.mri = mri
        self._request_queue = Queue()
        # {Part: Alarm} for current faults
        self._faults = {}
        # {Hook: name}
        self._hook_names = {}
        # {Hook: {Part: func_name}}
        self._hooked_func_names = {}
        self._find_hooks()
        # {part_name: (field_name, Model, setter)
        self.part_fields = OrderedDict()
        # {name: Part}
        self.parts = OrderedDict()
        self._lock = RLock(self.use_cothread)
        self._block = BlockModel()
        self._block.meta.set_description(description)
        self.set_label(mri)
        for part in parts:
            self.add_part(part)
        self._notifier = Notifier(mri, self._lock, self._block)
        self._block.set_notifier_path(self._notifier, [mri])
        self._write_functions = {}
        self._add_block_fields()

    def set_label(self, label):
        """Set the label of the Block Meta object"""
        self._block.meta.set_label(label)

    def add_part(self, part):
        assert part.name not in self.parts, \
            "Part %r already exists in Controller %r" % (part.name, self.mri)
        part.attach_to_controller(self)
        # Check part hooks into one of our hooks
        for func_name, part_hook, _ in get_hook_decorated(part):
            assert part_hook in self._hook_names, \
                "Part %s func %s not hooked into %s" % (
                    part.name, func_name, self)
            self._hooked_func_names[part_hook][part] = func_name
        part_fields = list(part.create_attribute_models()) + \
                      list(part.create_method_models())
        self.parts[part.name] = part
        self.part_fields[part.name] = part_fields

    def _find_hooks(self):
        for name, member in inspect.getmembers(self, Hook.isinstance):
            assert member not in self._hook_names, \
                "Hook %s already in %s as %s" % (
                    self, name, self._hook_names[member])
            self._hook_names[member] = name
            self._hooked_func_names[member] = {}

    def _add_block_fields(self):
        for iterable in (self.create_attribute_models(),
                         self.create_method_models(),
                         self.initial_part_fields()):
            for name, child, writeable_func in iterable:
                self.add_block_field(name, child, writeable_func)

    def add_block_field(self, name, child, writeable_func):
        if writeable_func:
            self._write_functions[name] = writeable_func
        if isinstance(child, AttributeModel):
            if writeable_func:
                child.meta.set_writeable(True)
            if not child.meta.label:
                child.meta.set_label(camel_to_title(name))
        elif isinstance(child, MethodModel):
            if writeable_func:
                child.set_writeable(True)
                for k, v in child.takes.elements.items():
                    v.set_writeable(True)
            if not child.label:
                child.set_label(camel_to_title(name))
        else:
            raise ValueError("Invalid block field %r" % child)
        self._block.set_endpoint_data(name, child)

    def create_method_models(self):
        """Provide MethodModel instances to be attached to BlockModel

        Yields:
            tuple: (string name, MethodModel, callable post_function).
        """
        return get_method_decorated(self)

    def create_attribute_models(self):
        """Provide AttributeModel instances to be attached to BlockModel

        Yields:
            tuple: (string name, AttributeModel, callable put_function).
        """
        # Create read-only attribute to show error texts
        meta = HealthMeta("Displays OK or an error message")
        self.health = meta.create_attribute_model()
        yield "health", self.health, None

    def initial_part_fields(self):
        for part_fields in self.part_fields.values():
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

    def update_health(self, part, alarm=None):
        """Set the health attribute. Called from part"""
        if alarm is not None:
            alarm = deserialize_object(alarm, Alarm)
        with self.changes_squashed:
            if alarm is None or not alarm.severity:
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
            self.health.set_value(text, alarm=alarm)

    def block_view(self):
        """Get a view of the block we control

        Returns:
            Block: The block we control
        """
        context = Context(self.process)
        return self.make_view(context)

    def make_view(self, context, data=None, child_name=None):
        """Make a child View of data[child_name]"""
        try:
            return self._make_view(context, data, child_name)
        except WrongThreadError:
            # called from wrong thread, spawn it again
            result = self.spawn(self._make_view, context, data, child_name)
            return result.get()

    def _make_view(self, context, data, child_name):
        """Called in cothread's thread"""
        with self._lock:
            if data is None:
                child = self._block
            else:
                child = data[child_name]
            child_view = self._make_appropriate_view(context, child)
        return child_view

    def _make_appropriate_view(self, context, data):
        if isinstance(data, BlockModel):
            # Make an Block View
            return make_block_view(self, context, data)
        elif isinstance(data, AttributeModel):
            # Make an Attribute View
            return Attribute(self, context, data)
        elif isinstance(data, MethodModel):
            # Make a Method View
            return Method(self, context, data)
        elif isinstance(data, Model):
            # Make a generic View of it
            return make_view(self, context, data)
        elif isinstance(data, dict):
            # Need to recurse down
            d = OrderedDict()
            for k, v in data.items():
                d[k] = self._make_appropriate_view(context, v)
            return d
        elif isinstance(data, list):
            # Need to recurse down
            return [self._make_appropriate_view(context, x) for x in data]
        else:
            return data

    def handle_request(self, request):
        """Spawn a new thread that handles Request"""
        # Put data on the queue, so if spawns are handled out of order we
        # still get the most up to date data
        self._request_queue.put(request)
        return self.spawn(self._handle_request)

    def _handle_request(self):
        responses = []
        with self._lock:
            # We spawned just above, so there is definitely something on the
            # queue
            request = self._request_queue.get(timeout=0)
            # self.log.debug(request)
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
                self.log.exception("Exception notifying %s", response)
                raise

    def _handle_get(self, request):
        """Called with the lock taken"""
        data = self._block
        for endpoint in request.path[1:]:
            try:
                data = data[endpoint]
            except KeyError:
                if hasattr(data, "typeid"):
                    typ = data.typeid
                else:
                    typ = type(data)
                raise UnexpectedError(
                    "Object of type %r has no attribute %r" % (typ, endpoint))
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
            part_contexts[part] = Context(self.process)
        return part_contexts

    def run_hook(self, hook, part_contexts, *args, **params):
        hook_queue, hook_runners = self.start_hook(
            hook, part_contexts, *args, **params)
        return_dict = self.wait_hook(hook_queue, hook_runners)
        return return_dict

    def start_hook(self, hook, part_contexts, *args, **params):
        assert hook in self._hook_names, \
            "Hook %s doesn't appear in controller hooks %s" % (
                hook, self._hook_names)
        hook_name = self._hook_names[hook]
        self.log.debug("%s: Starting hook", hook_name)

        # This queue will hold (part, result) tuples
        hook_queue = Queue()
        hook_queue.hook_name = hook_name
        hook_runners = {}

        # now start them off
        # Take the lock so that no hook abort can come in between now and
        # the spawn of the context
        with self._lock:
            for part, context in part_contexts.items():
                # context might have been aborted but have nothing servicing
                # the queue, we still want the legitimate messages on the queue
                # so just tell it to ignore stops it got before now
                context.ignore_stops_before_now()
                func_name = self._hooked_func_names[hook].get(part, None)
                if func_name:
                    hook_runners[part] = part.make_hook_runner(
                        hook_queue, func_name, weakref.proxy(context), *args,
                        **params)

        return hook_queue, hook_runners

    def wait_hook(self, hook_queue, hook_runners):
        # Wait for them all to finish
        return_dict = {}
        start = time.time()
        while hook_runners:
            part, ret = hook_queue.get()
            hook_runner = hook_runners.pop(part)

            # Wait for the process to terminate
            hook_runner.wait()
            return_dict[part.name] = ret
            duration = time.time() - start
            if hook_runners:
                self.log.debug(
                    "%s: Part %s returned %r after %ss. Still waiting for %s",
                    hook_queue.hook_name, part.name, ret, duration,
                    [p.name for p in hook_runners])
            else:
                self.log.debug(
                    "%s: Part %s returned %r after %ss. Returning...",
                    hook_queue.hook_name, part.name, ret, duration)

            if isinstance(ret, Exception):
                if not isinstance(ret, AbortedError):
                    # If AbortedError, all tasks have already been stopped.
                    # Got an error, so stop and wait all hook runners
                    for h in hook_runners.values():
                        h.stop()
                # Wait for them to finish
                for h in hook_runners.values():
                    h.wait(timeout=ABORT_TIMEOUT)
                raise ret

        return return_dict
