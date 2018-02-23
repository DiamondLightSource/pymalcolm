from contextlib import contextmanager

from annotypes import TYPE_CHECKING, Anno, Sequence, overload

from malcolm.compat import OrderedDict
from .context import Context
from .errors import UnexpectedError, WrongThreadError
from .hook import Hookable, start_hooks, wait_hooks, Hook
from .info import Info
from .models import BlockModel, AttributeModel, MethodModel, Model
from .notifier import Notifier
from .part import PartRegistrar, Part, FieldRegistry, InfoRegistry
from .queue import Queue
from .request import Get, Subscribe, Unsubscribe, Put, Post, Request
from .response import Response
from .rlock import RLock
from .serializable import serialize_object, camel_to_title
from .spawned import Spawned
from .views import make_view, Block

if TYPE_CHECKING:
    from typing import List, Dict, Tuple, Union, Callable, Any
    from .process import Process
    Field = Union[AttributeModel, MethodModel]
    CallbackResponses = List[Tuple[Callable[[Response], None], Response]]

# How long should we wait for spawned functions to complete after abort
ABORT_TIMEOUT = 5.0


with Anno("The Malcolm Resource Identifier for the Block produced"):
    AMri = str
with Anno("Description of the Block produced by the controller"):
    ADescription = str
with Anno("Whether the Controller should use cothread for its spawns"):
    AUseCothread = bool


class Controller(Hookable):
    process = None

    def __init__(self, mri, description="", use_cothread=True):
        # type: (AMri, ADescription, AUseCothread) -> None
        self.set_logger(mri=mri)
        self.name = mri
        self.mri = mri
        self.use_cothread = use_cothread
        self._request_queue = Queue()
        self.parts = OrderedDict()  # type: Dict[str, Part]
        self._lock = RLock(self.use_cothread)
        self._block = BlockModel()
        self._block.meta.set_description(description)
        self._block.meta.set_label(mri)
        self._notifier = Notifier(mri, self._lock, self._block)
        self._block.set_notifier_path(self._notifier, [mri])
        self._write_functions = {}
        self.field_registry = FieldRegistry()
        self.info_registry = InfoRegistry()

    def setup(self, process):
        # type: (Process) -> None
        self.process = process
        self.info_registry.set_spawn(self.spawn)
        self.add_initial_part_fields()

    def add_part(self, part):
        # type: (Part) -> None
        assert part.name not in self.parts, \
            "Part %r already exists in Controller %r" % (part.name, self.mri)
        part.setup(PartRegistrar(
            self.field_registry, self.info_registry, part))
        self.parts[part.name] = part

    def add_block_field(self, name, child, writeable_func):
        # type: (str, Field, Callable[..., Any]) -> None
        if isinstance(child, AttributeModel):
            meta = child.meta
        elif isinstance(child, MethodModel):
            meta = child
        else:
            raise ValueError("Invalid block field %r" % child)
        if writeable_func:
            self._write_functions[name] = writeable_func
            meta.set_writeable(True)
        if not meta.label:
            meta.set_label(camel_to_title(name))
        self._block.set_endpoint_data(name, child)

    def add_initial_part_fields(self):
        # type: () -> None
        for part_fields in self.field_registry.fields.values():
            for name, child, writeable_func in part_fields:
                self.add_block_field(name, child, writeable_func)

    def spawn(self, func, *args, **kwargs):
        # type: (Callable[..., Any], *Any, **Any) -> Spawned
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

    @overload
    def make_view(self, context=None):
        # type: (Context) -> Block
        pass

    @overload
    def make_view(self, context, data=None, child_name=None):
        # type: (Context, Model, str) -> Any
        pass

    def make_view(self, context=None, data=None, child_name=None):
        """Make a child View of data[child_name]"""
        try:
            ret = self._make_view(context, data, child_name)
        except WrongThreadError:
            # called from wrong thread, spawn it again
            result = self.spawn(self._make_view, context, data, child_name)
            ret = result.get()
        return ret

    def _make_view(self, context, data, child_name):
        # type: (Context, Model, str) -> Any
        """Called in cothread's thread"""
        with self._lock:
            if context is None:
                context = Context(self.process)
            if data is None:
                child = self._block
            else:
                child = data[child_name]
            child_view = make_view(self, context, child)
        return child_view

    def handle_request(self, request):
        # type: (Request) -> Spawned
        """Spawn a new thread that handles Request"""
        # Put data on the queue, so if spawns are handled out of order we
        # still get the most up to date data
        self._request_queue.put(request)
        return self.spawn(self._handle_request)

    def _handle_request(self):
        # type: () -> None
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
            except Exception:
                self.log.exception("Exception notifying %s", response)
                raise

    def _handle_get(self, request):
        # type: (Get) -> CallbackResponses
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
        # Important to serialize now with the lock so we get a consistent set
        serialized = serialize_object(data)
        ret = [request.return_response(serialized)]
        return ret

    def _handle_put(self, request):
        # type: (Put) -> CallbackResponses
        """Called with the lock taken"""
        attribute_name = request.path[1]

        attribute = self._block[attribute_name]
        assert attribute.meta.writeable, \
            "Attribute %s is not writeable" % attribute_name
        put_function = self._write_functions[attribute_name]
        value = attribute.meta.validate(request.value)

        with self.lock_released:
            result = put_function(value)

        # Don't need to serialize as the result is None, at the moment...
        ret = [request.return_response(result)]
        return ret

    def _handle_post(self, request):
        # type: (Post) -> CallbackResponses
        """Called with the lock taken"""
        method_name = request.path[1]
        if request.parameters:
            param_dict = request.parameters
        else:
            param_dict = {}

        method = self._block[method_name]  # type: MethodModel
        assert method.writeable, \
            "Method %s is not writeable" % method_name
        args = method.validate(param_dict)

        post_function = self._write_functions[method_name]

        with self.lock_released:
            result = post_function(**args)

        # Don't need to serialize as the result should be immutable
        ret = [request.return_response(result)]
        return ret

    def run_hooks(self, hooks):
        # type: (Sequence[Hook]) -> Dict[str, List[Info]]
        return self.wait_hooks(*self.start_hooks(hooks))

    def start_hooks(self, hooks):
        # type: (Sequence[Hook]) -> Tuple[Queue, List[Hook]]
        # Hooks might be a generator, so convert to a list
        hooks = list(hooks)
        if not hooks:
            return Queue(), []
        self.log.debug("%s: Starting hook", hooks[0].name)
        for hook in hooks:
            hook.set_spawn(self.spawn)
        # Take the lock so that no hook abort can come in between now and
        # the spawn of the context
        with self._lock:
            hook_queue, hook_spawned = start_hooks(hooks)
        return hook_queue, hook_spawned

    def wait_hooks(self, hook_queue, hook_spawned):
        # type: (Queue, List[Hook]) -> Dict[str, List[Info]]
        if hook_spawned:
            return_dict = wait_hooks(
                self.log, hook_queue, hook_spawned, ABORT_TIMEOUT)
        else:
            self.log.debug("No Parts hooked")
            return_dict = {}
        return return_dict
