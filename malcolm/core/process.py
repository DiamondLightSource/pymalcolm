from collections import OrderedDict, namedtuple

from malcolm.core.loggable import Loggable
from malcolm.core.request import Request
from malcolm.core.response import Response
from malcolm.core.cache import Cache
from malcolm.core.block import Block
from malcolm.core.attribute import Attribute
from malcolm.core.stringarraymeta import StringArrayMeta


# Sentinel object that when received stops the recv_loop
PROCESS_STOP = object()

def internal_request(type_, args):
    cls = namedtuple(type_, args)
    cls.type_ = type_
    return cls

# Internal update messages
BlockNotify = internal_request("BlockNotify", "name")
BlockChanged = internal_request("BlockChanged", "change")
BlockRespond = internal_request("BlockRespond", "response, response_queue")
BlockAdd = internal_request("BlockAdd", "block")
BlockList = internal_request("BlockList", "client_comms, blocks")


class Process(Loggable):
    """Hosts a number of Blocks, distributing requests between them"""

    def __init__(self, name, sync_factory):
        super(Process, self).__init__(logger_name=name)
        self.name = name
        self.sync_factory = sync_factory
        self.q = self.create_queue()
        self._blocks = OrderedDict()  # block name -> block
        self._block_state_cache = Cache()
        self._recv_spawned = None
        self._other_spawned = []
        self._subscriptions = OrderedDict()  # block name -> list of subs
        self._last_changes = OrderedDict()  # block name -> list of changes
        self._client_comms = OrderedDict()  # client comms -> list of blocks
        self._handle_functions = {
            Request.POST: self._forward_block_request,
            Request.PUT: self._forward_block_request,
            Request.GET: self._handle_get,
            Request.SUBSCRIBE: self._handle_subscribe,
            BlockNotify.type_: self._handle_block_notify,
            BlockChanged.type_: self._handle_block_changed,
            BlockRespond.type_: self._handle_block_respond,
            BlockAdd.type_: self._handle_block_add,
            BlockList.type_ : self._handle_block_list,
        }
        self.create_process_block()

    def recv_loop(self):
        """Service self.q, distributing the requests to the right block"""
        while True:
            request = self.q.get()
            self.log_debug("Received request %s", request)
            if request is PROCESS_STOP:
                # Got the sentinel, stop immediately
                break
            try:
                self._handle_functions[request.type_](request)
            except Exception:
                self.log_exception("Exception while handling %s", request)

    def start(self):
        """Start the process going"""
        self._recv_spawned = self.sync_factory.spawn(self.recv_loop)

    def stop(self, timeout=None):
        """Stop the process and wait for it to finish

        Args:
            timeout (float): Maximum amount of time to wait for each spawned
            process. None means forever
        """
        assert self._recv_spawned, "Process not started"
        self.q.put(PROCESS_STOP)
        # Wait for recv_loop to complete first
        self._recv_spawned.wait(timeout=timeout)
        # Now wait for anything it spawned to complete
        for s in self._other_spawned:
            s.wait(timeout=timeout)

    def _forward_block_request(self, request):
        """Lookup target Block and spawn block.handle_request(request)

        Args:
            request (Request): The message that should be passed to the Block
        """
        block_name = request.endpoint[0]
        block = self._blocks[block_name]
        self._other_spawned.append(
            self.sync_factory.spawn(block.handle_request, request))

    def create_queue(self):
        """
        Create a queue using sync_factory object

        Returns:
            Queue: New queue
        """

        return self.sync_factory.create_queue()

    def create_lock(self):
        """
        Create a lock using sync_factory object

        Returns:
            Lock: New lock
        """
        return self.sync_factory.create_lock()

    def spawn(self, function, *args, **kwargs):
        """Calls SyncFactory.spawn()"""
        spawned = self.sync_factory.spawn(function, *args, **kwargs)
        self._other_spawned.append(spawned)
        return spawned

    def get_client_comms(self, block_name):
        for client_comms, blocks in list(self._client_comms.items()):
            if block_name in blocks:
                return client_comms

    def create_process_block(self):
        self.process_block = Block(self.name)
        self.process_block.add_attribute(
            Attribute("blocks", StringArrayMeta(
                "meta", "Blocks hosted by this Process")))
        self.process_block.add_attribute(
            Attribute("remoteBlocks", StringArrayMeta(
                "meta", "Blocks reachable via ClientComms")))
        self.add_block(self.process_block)

    def update_block_list(self, client_comms, blocks):
        self.q.put(BlockList(client_comms=client_comms, blocks=blocks))

    def _handle_block_list(self, request):
        self._client_comms[request.client_comms] = request.blocks
        remotes = []
        for blocks in self._client_comms.values():
            remotes += [b for b in blocks if b not in remotes]
        self.process_block.remoteBlocks.set_value(remotes)

    def notify_subscribers(self, block_name):
        self.q.put(BlockNotify(name=block_name))

    def _handle_block_notify(self, request):
        """Update subscribers with changes and applies stored changes to the
        cached structure"""
        # update cached dict
        for delta in self._last_changes.setdefault(request.name, []):
            self._block_state_cache.delta_update(delta)

        for subscription in self._subscriptions.setdefault(request.name, []):
            endpoint = subscription.endpoint
            # find stuff that's changed that is relevant to this subscriber
            changes = []
            for change in self._last_changes[request.name]:
                change_path = change[0]
                # look for a change_path where the beginning matches the
                # endpoint path, then strip away the matching part and add
                # to the change set
                i = 0
                for (cp_element, ep_element) in zip(change_path, endpoint):
                    if cp_element != ep_element:
                        break
                    i += 1
                else:
                    # change has matching path, so keep it
                    # but strip off the end point path
                    filtered_change = [change_path[i:]] + change[1:]
                    changes.append(filtered_change)
            if len(changes) > 0:
                if subscription.delta:
                    # respond with the filtered changes
                    response = Response.Delta(
                        subscription.id_, subscription.context, changes)
                else:
                    # respond with the structure of everything
                    # below the endpoint
                    d = self._block_state_cache.walk_path(endpoint)
                    response = Response.Update(
                        subscription.id_, subscription.context, d)
                self.log_debug("Responding to subscription %s", response)
                subscription.response_queue.put(response)
        self._last_changes[request.name] = []

    def on_changed(self, change, notify=True):
        self.q.put(BlockChanged(change=change))
        if notify:
            block_name = change[0][0]
            self.notify_subscribers(block_name)

    def _handle_block_changed(self, request):
        """Record changes to made to a block"""
        # update changes
        path = request.change[0]
        block_changes = self._last_changes.setdefault(path[0], [])
        block_changes.append(request.change)

    def block_respond(self, response, response_queue):
        self.q.put(BlockRespond(response, response_queue))

    def _handle_block_respond(self, request):
        """Push the response to the required queue"""
        request.response_queue.put(request.response)

    def add_block(self, block):
        """Add a block to be hosted by this process

        Args:
            block (Block): The block to be added
        """
        assert block.name not in self._blocks, \
            "There is already a block called %s" % block.name
        self.q.put(BlockAdd(block=block))

    def _handle_block_add(self, request):
        """Add a block to be hosted by this process"""
        block = request.block
        assert block.name not in self._blocks, \
            "There is already a block called %s" % block.name
        self._blocks[block.name] = block
        self._block_state_cache[block.name] = block.to_dict()
        block.parent = self
        block.lock = self.create_lock()
        # Regenerate list of blocks
        self.process_block.blocks.set_value(list(self._blocks))

    def _handle_subscribe(self, request):
        """Add a new subscriber and respond with the current
        sub-structure state"""
        subs = self._subscriptions.setdefault(request.endpoint[0], [])
        subs.append(request)
        d = self._block_state_cache.walk_path(request.endpoint)
        self.log_debug("Initial subscription value %s", d)
        if request.delta:
            request.respond_with_delta([[[], d]])
        else:
            request.respond_with_update(d)

    def _handle_get(self, request):
        d = self._block_state_cache.walk_path(request.endpoint)
        response = Response.Return(request.id_, request.context, d)
        request.response_queue.put(response)
