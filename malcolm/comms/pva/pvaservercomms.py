from tornado.ioloop import IOLoop

from malcolm.core.cache import Cache
from malcolm.core.servercomms import ServerComms
from malcolm.core.serializable import Serializable
from malcolm.core.request import Request, Subscribe

class PvaServerComms(ServerComms):
    """A class for communication between pva client and server"""
    CACHE_UPDATE = 0

    def __init__(self, name, process):
        super(PvaServerComms, self).__init__(name, process)

        self.name = name
        self.process = process

        self._current_id = 1
        self._root_id = 0
        self._blocklist = {}
        self._cache = Cache()

        # Set up the subscription for everything (root down)
        request = Subscribe(None, self.q, [], True)
        request.set_id(self._root_id)
        self.process.q.put(request)

    def _update_block_list(self):
        old_blocks = self._blocklist.copy()
        for name in self._cache:
            if name in self._blocklist:
                old_blocks.pop(name)
            else:
                # New block, so create the new Pva endpoint
                self.log_debug("Adding block to PVA list: %s", name)
                self._current_id += 1
                self._blocklist[name] = self._current_id
                self._add_new_pva_channel(name)

        # Now loop over any remaining old blocks and remove their subscriptions
        for name in old_blocks:
            self.log_debug("Removing stale block: %s", name)

    def _update_cache(self, response):
        if response.changes:
            self.log_debug("Update received: %s", response.changes)
            self._cache.apply_changes(*response.changes)
            # Update the block list to create new PVA channels if required
            self._update_block_list()

    def send_to_client(self, response):
        """Abstract method to dispatch response to a client

        Args:
            response (Response): The message to pass to the client
        """
        # Update the cache
        self._update_cache(response)

    def _add_new_pva_channel(self, name):
        """Create a new PVA endpoint for the block name

        Args:
            name (str): The name of the block to create the PVA endpoint for
        """
        self.log_debug("Creating PVA endpoint for %s", name)
