import time

from annotypes import Anno, WithCallTypes

with Anno("The exposure to be active for"):
    Exposure = float
with Anno("The full path to the text file to write"):
    Path = str


class Simple(WithCallTypes):
    def __init__(self, exposure: Exposure, path: Path = "/tmp/file.txt"):
        self.exposure = exposure
        self.path = path

    def write_data(self, data: str):
        with open(self.path, "w") as f:
            time.sleep(self.exposure)
            f.write("Data: %s\n" % data)
