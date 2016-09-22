from collections import OrderedDict
import socket

from malcolm.core import Loggable, Spawnable


class PandABoxControl(Loggable, Spawnable):

    def __init__(self, process, hostname, port):
        self.set_logger_name("PandABoxControl(%s:%s)" % (hostname, port))
        self.process = process
        self.hostname = hostname
        self.port = port
        # Completed lines for a response in progress
        self._completed_response_lines = []
        # True if the current response is multiline
        self._is_multiline = None
        # This queue holds send messages
        self.q = process.create_queue()
        self.response_queues = process.create_queue()
        self.socket = socket.socket()
        self.socket.connect((hostname, port))
        self.add_spawn_function(self.send_loop,
                                self.make_default_stop_func(self.q))
        self.add_spawn_function(self.recv_loop, self.socket.close)

    def send_recv(self, message, timeout=1.0):
        """Send a message to a PandABox and wait for the response

        Args:
            message (str): The message to send
            timeout (float): How long to wait before raising queue.Empty

        Returns:
            str: The response
        """
        response_queue = self.process.create_queue()
        self.response_queues.put(response_queue)
        self.q.put(message)
        response = response_queue.get(timeout=timeout)
        if isinstance(response, Exception):
            raise response
        else:
            return response

        try:
            return response_queue.get(timeout=timeout)
        except:
            self.response_queues.remove(response_queue)
            raise

    def send_loop(self):
        """Service self.q, sending requests to server"""
        while True:
            message = self.q.get()
            if message is Spawnable.STOP:
                break
            try:
                self.socket.send(message)
            except Exception:  # pylint:disable=broad-except
                self.log_exception(
                    "Exception sending message %s", message)

    def get_lines(self):
        buf = ""
        while True:
            lines = buf.split("\n")
            for line in lines[:-1]:
                # print "Yield", repr(line)
                yield line
            buf = lines[-1]
            # Get something new from the socket
            rx = self.socket.recv(4096)
            if rx:
                buf += rx

    def _respond(self, resp):
        """Respond to the person waiting"""
        response_queue = self.response_queues.get(timeout=0.1)
        response_queue.put(resp)
        self._completed_response_lines = []
        self._is_multiline = None

    def recv_loop(self):
        """Service socket recv, returning responses to the correct queue"""
        self._completed_response_lines = []
        self._is_multiline = None
        lines_iterator = self.get_lines()
        while True:
            try:
                line = next(lines_iterator)
                if self._is_multiline is None:
                    self._is_multiline = line.startswith("!") or line == "."
                if line.startswith("ERR"):
                    self._respond(ValueError(line))
                elif self._is_multiline:
                    if line == ".":
                        self._respond(self._completed_response_lines)
                    else:
                        assert line[0] == "!", \
                            "Multiline response {} doesn't start with !" \
                                .format(repr(line))
                        self._completed_response_lines.append(line[1:])
                else:
                    self._respond(line)
            except Exception:
                self.log_exception(
                    "Exception receiving message")

    def get_num_blocks(self):
        num_blocks = OrderedDict()
        for line in self.send_recv("*BLOCKS?\n"):
            block, num = line.split()
            num_blocks[block] = int(num)
        return num_blocks

    def get_field_data(self, block):
        results = {}
        for line in self.send_recv("{}.*?\n".format(block)):
            data = line.split()
            assert len(data) in (3, 4), \
                "Expected field_data to have len 3 or 4, got {}"\
                .format(len(data))
            if len(data) == 3:
                data.append("")
            name, index, cls, typ = data
            results[int(index)] = (name, cls, typ)
        field_data = OrderedDict()
        for _, (name, cls, typ) in sorted(results.items()):
            field_data[name] = (cls, typ)
        return field_data

    def get_enum_labels(self, block, field):
        enum_labels = []
        for line in self.send_recv("{}.{}.LABELS?\n".format(block, field)):
            enum_labels.append(line)
        return enum_labels

    def get_changes(self):
        changes = OrderedDict()
        for line in self.send_recv("*CHANGES?\n"):
            if line.endswith("(error)"):
                field = line.split(" ", 1)[0]
                val = Exception
            elif "<" in line:
                # table
                field = None
                val = None
            else:
                field, val = line.split("=", 1)
            changes[field] = val
        return changes

    def set_field(self, block, field, value):
        resp = self.send_recv("{}.{}={}\n".format(block, field, value))
        assert resp == "OK", \
            "Expected OK, got {}".format(resp)

    def get_bits(self):
        bits = []
        for i in range(4):
            bits += self.send_recv("*BITS{}?\n".format(i))
        return bits

    def get_positions(self):
        return self.send_recv("*POSITIONS?\n")
