from collections import OrderedDict

from malcolm.core.loggable import Loggable


# Sentinel object that when received stops the recv_loop
PROCESS_STOP = object()


class Process(Loggable):
    """Hosts a number of Blocks, distributing requests between them"""

    def __init__(self, name, scheduler):
        super(Process, self).__init__(logger_name=name)
        self.name = name
        self.scheduler = scheduler
        self.q = scheduler.create_queue()
        # map block name -> block object
        self._blocks = OrderedDict()
        self._recv_spawned = None
        self._other_spawned = []

    def recv_loop(self):
        """Service self.q, distributing the requests to the right block"""
        while True:
            request = self.q.get()
            if request is PROCESS_STOP:
                # Got the sentinel, stop immediately
                break
            try:
                self.handle_request(request)
            except Exception:
                # TODO: request.respond_with_error()
                self.log_exception("Exception while handling %s",
                                   request.to_dict())

    def start(self):
        """Start the process going"""
        self._recv_spawned = self.scheduler.spawn(self.recv_loop)

    def stop(self, timeout=None):
        """Stop the process and wait for it to finish

        Args:
            timeout (float): Maximum amount of time to wait. None means forever
        """
        assert self._recv_spawned, "Process not started"
        self.q.put(PROCESS_STOP)
        for s in self._other_spawned + [self._recv_spawned]:
            s.wait(timeout=timeout)

    def handle_request(self, request):
        """Lookup target Block and spawn block.handle_request(request)

        Args:
            request (Request): The message that should be passed to the Block
        """
        block_name = request.endpoint[0]
        block = self._blocks[block_name]
        self._other_spawned.append(
            self.scheduler.spawn(block.handle_request, request))

    def add_block(self, block):
        """Add a block to be hosted by this process

        Args:
            block (Block): The block to be added
        """
        assert block.name not in self._blocks, \
            "There is already a block called %s" % block.name
        self._blocks[block.name] = block
