from malcolm.core import Controller, Post, Subscribe, Return, MethodMeta, \
    method_takes, Error, Attribute, Put, Map


@method_takes()
class ClientController(Controller):
    """Sync a local block with a given remote block"""
    REMOTE_BLOCKS_ID = 0
    BLOCK_ID = 1

    def do_initial_reset(self):
        request = Subscribe(
            None, self, [self.process.name, "remoteBlocks", "value"])
        request.set_id(self.REMOTE_BLOCKS_ID)
        self.process.q.put(request)

    def put(self, response):
        """We don't have a queue as no thread to service, but act like one"""
        if response.id == self.REMOTE_BLOCKS_ID:
            if response.value and self.block_name in response.value:
                # process knows how to get to a block
                self._subscribe_to_block(self.block_name)
        elif response.id == self.BLOCK_ID:
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

        self.block.replace_endpoints(d)

        writeable_functions = {}
        for name in self.block:
            child = self.block[name]
            if isinstance(child, MethodMeta):
                # calling method forwards to server
                writeable_functions[name] = self.call_server_method
            elif isinstance(child, Attribute):
                # putting attribute forwards to server
                writeable_functions[name] = self.put_server_attribute

        self.block.set_writeable_functions(writeable_functions)

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
            attribute (Attribute): Attribute object to put a value to
            value (object: Value to put
        """
        ret = self._send_request(
            Put, attribute.path_relative_to(self.process) + ["value"], value)
        return ret

    def call_server_method(self, methodmeta, parameters=None, returns=None):
        """Call method_name on the server

        Args:
            methodmeta (MethodMeta): MethodMeta object to call
            parameters (Map): Map of arguments to be called with
            returns (Map): Returns map to fill and return
        """
        ret = self._send_request(
            Post, methodmeta.path_relative_to(self.process), parameters)
        if ret is not None:
            ret = Map(methodmeta.returns, ret)
        return ret
