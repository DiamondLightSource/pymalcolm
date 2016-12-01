from malcolm.core.loggable import Loggable
from malcolm.core.serializable import Serializable, serialize_object


class Monitorable(Loggable, Serializable):
    process = None
    process_path = []

    def set_process_path(self, process, process_path):
        """Sets the path from the Process

        Args:
            process (Process): The Process to attach to
            process_path (list[str]): The path to get to this object from
                Process
        """
        self.process = process
        process_path = list(process_path)
        self.process_path = process_path
        self.set_logger_name(".".join(process_path))
        for endpoint in self:
            attr = self[endpoint]
            if hasattr(attr, "set_process_path"):
                attr.set_process_path(process, process_path + [endpoint])

    def set_endpoint_data(self, name, value, notify=True):
        # set parent first so that we don't put something in the tree that
        # doesn't know how to get the path to the top of the tree
        process_path = self.process_path + [name]
        if hasattr(value, "set_process_path") and self.process:
            value.set_process_path(self.process, process_path)
        super(Monitorable, self).set_endpoint_data(name, value)
        if notify and self.process:
            self.process.report_changes(
                [process_path, serialize_object(value)])

    def apply_changes(self, *changes):
        serialized_changes = []
        for path, value in changes:
            ob = self
            for node in path[:-1]:
                ob = ob[node]
            attr = path[-1]
            setter = getattr(ob, "set_%s" % attr)
            setter(value, notify=False)
            serialized = serialize_object(ob[attr])
            serialized_changes.append([self.process_path + path, serialized])
        if self.process:
            self.process.report_changes(*serialized_changes)

