import functools
from collections import OrderedDict

from malcolm.core import Controller,  Post, Subscribe, Return, MethodMeta, \
    takes, Serializable, Error, Attribute, Put


@takes()
class ClientController(Controller):
    """Sync a local block with a given remote block"""
    REMOTE_BLOCKS_ID = 0
    BLOCK_ID = 1

    def __init__(self, block_name, process, parts=None, params=None):
        super(ClientController, self).__init__(
            block_name, process, parts, params)
        request = Subscribe(
            None, self, [self.process.name, "remoteBlocks", "value"])
        request.set_id(self.REMOTE_BLOCKS_ID)
        self.process.q.put(request)

    def put(self, response):
        """We don't have a queue as no thread to service, but act like one"""
        if response.id_ == self.REMOTE_BLOCKS_ID:
            if response.value and self.block_name in response.value:
                # process knows how to get to a block
                self._subscribe_to_block(self.block_name)
        elif response.id_ == self.BLOCK_ID:
            self.log_debug(response)
            # find all the regenerate block changesets
            regenerate = [c for c in response.changes if c[0] == []]
            if regenerate:
                assert len(response.changes) == 1, \
                    "Can only get regenerate message once in a changeset"
                value = regenerate[0][1]
                self._regenerate_block(value)
            else:
                # just hand it off to the block
                self.block.apply_changes(*response.changes)

    def _regenerate_block(self, d):
        children = OrderedDict()
        writeable_functions = {}
        for k, v in d.items():
            if k == "typeid":
                continue
            child = Serializable.from_dict(v)
            children[k] = child
            if isinstance(child, MethodMeta):
                # calling method forwards to server
                writeable_functions[k] = self.call_server_method
            elif isinstance(child, Attribute):
                # putting attribute forwards to server
                writeable_functions[k] = self.put_server_attribute
        self.block.set_children(children, writeable_functions)

    def _subscribe_to_block(self, block_name):
        self.client_comms = self.process.get_client_comms(block_name)
        assert self.client_comms, \
            "Process doesn't know about block %s" % block_name
        request = Subscribe(None, self, [block_name], delta=True)
        request.set_id(self.BLOCK_ID)
        self.client_comms.q.put(request)

    def _send_request(self, rtype, *args):
        q = self.process.create_queue()
        request = rtype(None, q, *args)
        self.client_comms.q.put(request)
        response = q.get()
        if isinstance(response, Return):
            return response.value
        elif isinstance(response, Error):
            raise ValueError(response.message)
        else:
            raise ValueError("Expected Return, got %s" % response.typeid)

    def put_server_attribute(self, attribute, value):
        """Put attribute value on the server

        Args:
            attribute_name (str): Name of the method
            value (object: Value to put
        """
        ret = self._send_request(
            Put, [self.block_name, attribute.name, "value"], value)
        return ret

    def call_server_method(self, methodmeta, parameters=None, returns=None):
        """Call method_name on the server

        Args:
            method_name (str): Name of the method
            parameters (Map): Map of arguments to be called with
            returns (Map): Returns map to fill and return
        """
        ret = self._send_request(
            Post, [self.block_name, methodmeta.name], parameters)
        return ret
