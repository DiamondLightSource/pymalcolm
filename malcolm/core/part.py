from malcolm.core.loggable import Loggable

class Part(Loggable):

    def __init__(self, name, process, block):
        self.process = process
        self.block = block
        self.name = name
        self.set_logger_name("%s.%s" % (block, name))
