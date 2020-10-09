import fcntl
import logging
import os
import socket
import struct
from typing import Dict, Optional

import cothread
from annotypes import Anno, add_call_types, deserialize_object, json_decode, json_encode
from tornado.websocket import WebSocketError, WebSocketHandler

from malcolm.core import (
    Delta,
    Error,
    FieldError,
    Part,
    PartRegistrar,
    Post,
    Put,
    Queue,
    Request,
    Response,
    Subscribe,
    Unsubscribe,
    Update,
)
from malcolm.modules import builtin

from ..hooks import ReportHandlersHook, UHandlerInfos
from ..infos import HandlerInfo
from ..util import IOLoopHelper

# Create a module level logger
log = logging.getLogger(__name__)

# Signals we can send to get info
SIOCGIFADDR = 0x8915
SIOCGIFNETMASK = 0x891B

# Where we get info about interfaces on Linux
SYSNET = "/sys/class/net"


def get_if_info(s, sig, ifname):
    # Use an ioctl to get interface address or netmask
    packed_ifname = struct.pack("256s", ifname[:15].encode())
    info = fcntl.ioctl(s.fileno(), sig, packed_ifname)
    return struct.unpack("!I", info[20:24])[0]


def get_ip_validator(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ifaddr = get_if_info(s, SIOCGIFADDR, ifname)
    ifnetmask = get_if_info(s, SIOCGIFNETMASK, ifname)

    def validator(remoteaddr):
        return remoteaddr & ifnetmask == ifaddr & ifnetmask

    return validator


# For some reason tornado doesn't make us implement all abstract methods
# noinspection PyAbstractClass
class MalcWebSocketHandler(WebSocketHandler):
    _registrar: PartRegistrar
    _id_to_mri: Dict[int, str]
    _validators = None
    _writeable = None
    _queue: Optional[Queue] = None
    _counter = None

    def initialize(self, registrar=None, validators=()):
        self._registrar = registrar
        # {id: mri}
        self._id_to_mri = {}
        self._validators = validators
        self._queue = Queue()
        self._counter = 0

    def on_message(self, message):
        # called in tornado's thread
        if self._writeable is None:
            ipv4_ip = self.request.remote_ip
            if ipv4_ip == "::1":
                # Special case IPV6 loopback
                ipv4_ip = "127.0.0.1"
            remoteaddr = struct.unpack("!I", socket.inet_aton(ipv4_ip))[0]
            if self._validators:
                # Work out if the remote ip is within the netmask of any of our
                # interfaces. If not, Put and Post are forbidden
                self._writeable = max(v(remoteaddr) for v in self._validators)
            else:
                self._writeable = True
            log.info(
                "Puts and Posts are %s from %s",
                "allowed" if self._writeable else "forbidden",
                self.request.remote_ip,
            )

        msg_id = -1
        try:
            d = json_decode(message)
            try:
                msg_id = d["id"]
            except KeyError:
                raise FieldError("id field not present in JSON message")
            request = deserialize_object(d, Request)
            request.set_callback(self.on_response)
            if isinstance(request, Subscribe):
                assert msg_id not in self._id_to_mri, (
                    "Duplicate subscription ID %d" % msg_id
                )
                self._id_to_mri[msg_id] = request.path[0]
            if isinstance(request, Unsubscribe):
                mri = self._id_to_mri[msg_id]
            else:
                mri = request.path[0]
            if isinstance(request, (Put, Post)) and not self._writeable:
                raise ValueError(
                    "Put/Post is forbidden from %s" % self.request.remote_ip
                )
            self._registrar.report(builtin.infos.RequestInfo(request, mri))
        except Exception as e:
            log.exception("Error handling message:\n%s", message)
            error = Error(msg_id, e)
            error_message = error.to_dict()
            self.write_message(json_encode(error_message))

    def on_response(self, response):
        # called from cothread
        IOLoopHelper.call(self._on_response, response)
        # Wait for completion once every 10 message
        self._counter += 1
        if self._counter % 10 == 0:
            for _ in range(10):
                self._queue.get()

    def _on_response(self, response: Response) -> None:
        # called from tornado thread
        message = json_encode(response)
        try:
            self.write_message(message)
        except WebSocketError:
            # The websocket is dead. If the response was a Delta or Update, then
            # unsubscribe so the local controller doesn't keep on trying to
            # respond
            if isinstance(response, (Delta, Update)):
                # Websocket is dead so we can clear the subscription key.
                # Subsequent updates may come in before the unsubscribe, but
                # ignore them as we can't do anything about it
                mri = self._id_to_mri.pop(response.id, None)
                if mri:
                    log.info("WebSocket Error: unsubscribing from stale handle")
                    unsubscribe = Unsubscribe(response.id)
                    unsubscribe.set_callback(self.on_response)
                    if self._registrar:
                        self._registrar.report(
                            builtin.infos.RequestInfo(unsubscribe, mri)
                        )
        finally:
            assert self._queue, "No queue"
            cothread.Callback(self._queue.put, None)

    # http://stackoverflow.com/q/24851207
    # TODO: remove this when the web gui is hosted from the box
    def check_origin(self, origin):
        return True


with Anno("Part name and subdomain name to host websocket on"):
    AName = str
with Anno("If True, check any client is in the same subnet as the host"):
    ASubnetValidation = bool


class WebsocketServerPart(Part):
    def __init__(
        self, name: AName = "ws", subnet_validation: ASubnetValidation = True
    ) -> None:
        super().__init__(name)
        self.subnet_validation = subnet_validation

    def setup(self, registrar: PartRegistrar) -> None:
        super().setup(registrar)
        # Hooks
        registrar.hook(ReportHandlersHook, self.on_report_handlers)

    @add_call_types
    def on_report_handlers(self) -> UHandlerInfos:
        validators = []
        if self.subnet_validation:
            # Create an ip validator for every interface that is up
            for ifname in os.listdir(SYSNET):
                with open(os.path.join(SYSNET, ifname, "operstate")) as f:
                    state = str(f.read())
                if state != "down\n":
                    # interface is up
                    validators.append(get_ip_validator(ifname))
        info = HandlerInfo(
            r"/%s" % self.name,
            MalcWebSocketHandler,
            registrar=self.registrar,
            validators=validators,
        )
        return info
