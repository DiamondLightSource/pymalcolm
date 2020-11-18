from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Tuple, Union

from annotypes import Anno, stringify_error

from malcolm.compat import OrderedDict

from .alarm import Alarm
from .camel import camel_to_title
from .concurrency import Queue, RLock, Spawned
from .context import Context
from .errors import FieldError, NotWriteableError, UnexpectedError
from .hook import Hook, Hookable, start_hooks, wait_hooks
from .info import Info
from .models import AttributeModel, BlockModel, MethodLog, MethodModel, Model
from .notifier import Notifier, freeze
from .part import FieldRegistry, InfoRegistry, Part, PartRegistrar
from .request import Get, Post, Put, Request, Subscribe, Unsubscribe
from .response import Response
from .tags import method_return_unpacked, version_tag
from .timestamp import TimeStamp
from .views import Block, make_view

Field = Union[AttributeModel, MethodModel]
CallbackResponses = List[Tuple[Callable[[Response], None], Response]]
if TYPE_CHECKING:
    from .process import Process

# This is a good default value for a timeout. It is used to wait for abort
# below, and is imported in a number of other Controller subclasses
DEFAULT_TIMEOUT = 10.0


with Anno("The Malcolm Resource Identifier for the Block produced"):
    AMri = str
with Anno("Description of the Block produced by the controller"):
    ADescription = str


class Controller(Hookable):
    process = None

    def __init__(self, mri: AMri, description: ADescription = "") -> None:
        self.set_logger(mri=mri)
        self.name = mri
        self.mri = mri
        self.parts: Dict[str, Part] = OrderedDict()
        self._lock = RLock()
        self._block = BlockModel()
        self._block.meta.set_description(description)
        self._block.meta.set_label(mri)
        self._block.meta.set_tags([version_tag()])
        self._notifier = Notifier(mri, self._lock, self._block)
        self._block.set_notifier_path(self._notifier, [mri])
        self._write_functions: Dict[str, Callable[..., Any]] = {}
        self.field_registry = FieldRegistry()
        self.info_registry = InfoRegistry()

    def setup(self, process: "Process") -> None:
        self.process = process
        self.add_initial_part_fields()

    def add_part(self, part: Part) -> None:
        assert (
            part.name not in self.parts
        ), "Part %r already exists in Controller %r" % (part.name, self.mri)
        part.setup(PartRegistrar(self.field_registry, self.info_registry, part))
        self.parts[part.name] = part

    def add_block_field(
        self,
        name: str,
        child: Field,
        writeable_func: Callable[..., Any],
        needs_context: bool,
    ) -> None:
        if writeable_func:
            if needs_context:
                # Wrap func
                def func_wrapper(*args, **kwargs):
                    return writeable_func(Context(self.process), *args, **kwargs)

                self._write_functions[name] = func_wrapper
            else:
                self._write_functions[name] = writeable_func
            child.meta.set_writeable(True)
        if not child.meta.label:
            child.meta.set_label(camel_to_title(name))
        self._block.set_endpoint_data(name, child)

    def add_initial_part_fields(self) -> None:
        for part_fields in self.field_registry.fields.values():
            for name, child, writeable_func, needs_context in part_fields:
                self.add_block_field(name, child, writeable_func, needs_context)

    @property  # type: ignore
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

    def block_view(self, context: Context = None) -> Block:
        if context is None:
            assert self.process, "No process for context."
            context = Context(self.process)
        with self._lock:
            child_view = make_view(self, context, self._block)
        return child_view

    def make_view(self, context: Context, data: Model, child_name: str) -> Any:
        """Make a child View of data[child_name]"""
        with self._lock:
            child = data[child_name]
            child_view = make_view(self, context, child)
        return child_view

    def handle_request(self, request: Request) -> Spawned:
        """Spawn a new thread that handles Request"""
        assert self.process, "No process to handle request"
        return self.process.spawn(self._handle_request, request)

    def _handle_request(self, request: Request) -> None:
        responses = []
        with self._lock:
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
                self.log.exception(f"Exception notifying {response}")
                raise

    def _handle_get(self, request: Get) -> CallbackResponses:
        """Called with the lock taken"""
        data = self._block

        for i, endpoint in enumerate(request.path[1:]):
            try:
                data = data[endpoint]
            except KeyError:
                if hasattr(data, "typeid"):
                    typ = data.typeid
                else:
                    typ = type(data)
                path = ".".join(request.path[: i + 1])
                raise UnexpectedError(
                    "Object '%s' of type %r has no attribute '%s'"
                    % (path, typ, endpoint)
                )
        # Important to freeze now with the lock so we get a consistent set
        serialized = freeze(data)
        ret = [request.return_response(serialized)]
        return ret

    def check_field_writeable(self, field):
        if not field.meta.writeable:
            raise NotWriteableError("Field %s is not writeable" % field.path)

    def get_put_function(self, attribute_name):
        return self._write_functions[attribute_name]

    def _handle_put(self, request: Put) -> CallbackResponses:
        """Called with the lock taken"""
        attribute_name = request.path[1]

        try:
            attribute = self._block[attribute_name]
        except KeyError:
            raise FieldError(
                "Block '%s' has no Attribute '%s'" % (self.mri, attribute_name)
            )

        assert isinstance(
            attribute, AttributeModel
        ), "Cannot Put to %s which is a %s" % (attribute.path, type(attribute))
        self.check_field_writeable(attribute)

        put_function = self.get_put_function(attribute_name)
        value = attribute.meta.validate(request.value)

        with self.lock_released:
            result = put_function(value)

        if request.get and result is None:
            # We asked for a Get, and didn't get given a return, so do return
            # the current value. Don't serialize here as value is immutable
            # (as long as we don't try too hard to break the rules)
            result = self._block[attribute_name].value
        elif not request.get:
            # We didn't ask for a Get, so throw result away
            result = None
        ret = [request.return_response(result)]
        return ret

    def get_post_function(self, method_name):
        return self._write_functions[method_name]

    def update_method_logs(
        self, method, took_value, took_ts, returned_value, returned_alarm
    ):
        with self.changes_squashed:
            method.set_took(
                MethodLog(
                    value=method.meta.takes.validate(took_value, add_missing=True),
                    present=[x for x in method.meta.takes.elements if x in took_value],
                    timeStamp=took_ts,
                )
            )
            method.set_returned(
                MethodLog(
                    value=method.meta.returns.validate(
                        returned_value, add_missing=True
                    ),
                    present=[
                        x for x in method.meta.returns.elements if x in returned_value
                    ],
                    alarm=returned_alarm,
                )
            )

    def _handle_post(self, request: Post) -> CallbackResponses:
        """Called with the lock taken"""
        method_name = request.path[1]

        try:
            method = self._block[method_name]
        except KeyError:
            raise FieldError("Block '%s' has no Method '%s'" % (self.mri, method_name))

        assert isinstance(method, MethodModel), "Cannot Post to %s which is a %s" % (
            method.path,
            type(method),
        )
        self.check_field_writeable(method)

        post_function = self.get_post_function(method_name)
        took_ts = TimeStamp()
        took_value = method.meta.takes.validate(request.parameters)
        returned_alarm = Alarm.ok
        returned_value = {}

        try:
            with self.lock_released:
                result = post_function(**took_value)
            if method_return_unpacked() in method.meta.tags:
                # Single element, wrap in a dict
                returned_value = {"return": result}
            elif result is None:
                returned_value = {}
            else:
                # It should already be an object that serializes to a dict
                returned_value = result
        except Exception as e:
            returned_alarm = Alarm.major(stringify_error(e))
            raise
        finally:
            self.update_method_logs(
                method, took_value, took_ts, returned_value, returned_alarm
            )

        # Don't need to freeze as the result should be immutable
        ret = [request.return_response(result)]
        return ret

    def run_hooks(self, hooks: Iterable[Hook]) -> Dict[str, List[Info]]:
        return self.wait_hooks(*self.start_hooks(hooks))

    def start_hooks(self, hooks: Iterable[Hook]) -> Tuple[Queue, List[Hook]]:
        # Hooks might be a generator, so convert to a list
        hooks = list(hooks)
        if not hooks:
            return Queue(), []
        self.log.debug(f"{self.mri}: {hooks[0].name}: Starting hook")
        assert self.process, "No process for starting hooks"
        for hook in hooks:
            hook.set_spawn(self.process.spawn)
        # Take the lock so that no hook abort can come in between now and
        # the spawn of the context
        with self._lock:
            hook_queue, hook_spawned = start_hooks(hooks)
        return hook_queue, hook_spawned

    def wait_hooks(
        self, hook_queue: Queue, hook_spawned: List[Hook]
    ) -> Dict[str, List[Info]]:
        if hook_spawned:
            return_dict = wait_hooks(
                self.log, hook_queue, hook_spawned, DEFAULT_TIMEOUT
            )
        else:
            self.log.debug(f"{self.mri}: No Parts hooked")
            return_dict = {}
        return return_dict
