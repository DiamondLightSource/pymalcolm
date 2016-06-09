from collections import OrderedDict, namedtuple

from malcolm.core.loggable import Loggable


# Sentinel object that when received stops the recv_loop
PROCESS_STOP = object()

# Internal update messages
BlockNotify = namedtuple("BlockNotify", "name")
BlockChanged = namedtuple("BlockChanged", "changes")


class Process(Loggable):
    """Hosts a number of Blocks, distributing requests between them"""

    def __init__(self, name, sync_factory):
        super(Process, self).__init__(logger_name=name)
        self.name = name
        self.sync_factory = sync_factory
        self.q = self.create_queue()
        # map block name -> block object
        self._blocks = OrderedDict()
        self._block_state_cache = OrderedDict()
        self._recv_spawned = None
        self._other_spawned = []
        self._subscriptions = []
        self._last_changes = []

    def recv_loop(self):
        """Service self.q, distributing the requests to the right block"""
        while True:
            request = self.q.get()
            self.log_debug("Received request %s", request)
            if request is PROCESS_STOP:
                # Got the sentinel, stop immediately
                break
            elif isinstance(request, BlockNotify):
                self._handle_block_notify(request)
            elif isinstance(request, BlockChanged):
                self._handle_block_changed(request)
            else:
                try:
                    self.handle_request(request)
                except Exception:
                    # TODO: request.respond_with_error()
                    self.log_exception("Exception while handling %s",
                                       request.to_dict())

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

    def handle_request(self, request):
        """Lookup target Block and spawn block.handle_request(request)

        Args:
            request (Request): The message that should be passed to the Block
        """
        block_name = request.endpoint[0]
        block = self._blocks[block_name]
        self._other_spawned.append(
            self.sync_factory.spawn(block.handle_request, request))

    def add_block(self, block):
        """Add a block to be hosted by this process

        Args:
            block (Block): The block to be added
        """
        assert block.name not in self._blocks, \
            "There is already a block called %s" % block.name
        self._blocks[block.name] = block
        self._block_state_cache[block.name] = block.to_dict()

    def create_queue(self):
        """
        Create a queue using sync_factory object

        Returns:
            Queue: New queue
        """

        return self.sync_factory.create_queue()

    def spawn(self, function, *args, **kwargs):
        """Calls SyncFactory.spawn()"""
        spawned = self.sync_factory.spawn(function, *args, **kwargs)
        self._other_spawned.append(spawned)
        return spawned

    def _handle_block_notify(self, request):
        """Update subscribers with changes and applies stored changes to the
        cached structure"""

        # update cached dict
        for path, value in self._last_changes:
            d = self._block_state_cache
            for p in path[:-1]:
                d = d[p]
            d[path[-1]] = value

        for subscription in self._subscriptions:
            # find stuff that's changed that is relevant to this subscriber
            endpoint = subscription.endpoint
            changes = []
            for change_path, change_value in self._last_changes:
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
                    filtered_change = [change_path[i:], change_value]
                    changes.append(filtered_change)

            if subscription.delta:
                # respond with the filtered changes
                subscription.response_queue.put(changes)
            elif len(changes) > 0:
                # respond with the structure of everything below the endpoint
                update = self._block_state_cache
                for p in endpoint:
                    update = update[p]
                subscription.response_queue.put(update)

    def _handle_block_changed(self, request):
        """Record changes to made to a block"""
        for path, value in request.changes:
            # update changes
            for e in self._last_changes:
                if e[0] == path:
                    e[1] = value
                    break
            else:
                self._last_changes.append([path, value])


    def notify_subscribers(self, block_name):
        self.q.put(BlockNotify(name=block_name))

    def on_changed(self, changes):
        self.q.put(BlockChanged(changes=changes))
