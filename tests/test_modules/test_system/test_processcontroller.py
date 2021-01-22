import os
import subprocess
import time
import unittest
from math import floor

import cothread
from cothread import catools

from malcolm import __version__
from malcolm.core import Process
from malcolm.modules.system.controllers import ProcessController
from malcolm.modules.system.defines import redirector_iocs


class TestProcessController(unittest.TestCase):
    prefix = "unitTest:%s" % floor(time.time()).__repr__()[:-2]

    def setUp(self):
        self.process = Process("proc")
        self.o = ProcessController("MyMRI", self.prefix, "/tmp")
        self.process.add_controller(self.o)
        self.process.start()
        self.b = self.process.block_view("MyMRI")

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_sets_stats(self):
        # In unit tests, this depends on where the test-runner is run from
        assert self.b.pymalcolmVer.value in ["work", __version__]
        hostname = os.uname()[1]
        hostname = hostname if len(hostname) < 39 else hostname[:35] + "..."
        assert self.b.hostname.value == hostname

    def test_starts_ioc(self):
        cothread.Sleep(5)
        assert catools.caget(self.prefix + ":PYMALCOLM:VER") in ["work", __version__]

    def test_ioc_ticks(self):
        cothread.Sleep(5)
        uptime = catools.caget(self.prefix + ":UPTIME:RAW")
        assert uptime >= 0
        time.sleep(5)
        assert catools.caget(self.prefix + ":UPTIME:RAW") >= uptime + 5


class TestParseYamlVersion(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir("/tmp/prod")
        except OSError:
            pass
        self.testArea = "/tmp/prod/testpath-" + floor(time.time()).__repr__()[:-2]
        os.mkdir(self.testArea)
        self.cwd = os.getcwd()

        self.obj = ProcessController("", "", "/tmp")

    def tearDown(self):
        os.chdir(self.cwd)
        print(["rm", "-rf", self.testArea])
        subprocess.call(["rm", "-rf", self.testArea])
        os.rmdir("/tmp/prod")

    def test_simple_path_parse(self):
        assert (
            self.obj.parse_yaml_version(
                "/not/work/or/prod/something.yaml", "/tmp/work/", "/tmp/prod"
            )
            == "unknown"
        )
        assert (
            self.obj.parse_yaml_version(
                "/tmp/work/something.yaml", "/tmp/work/", "/tmp/prod"
            )
            == "work"
        )
        assert (
            self.obj.parse_yaml_version(
                self.testArea + "/something.yaml", "/tmp/work/", self.testArea
            )
            == "Prod (unknown version)"
        )

    def test_git_tag_parse(self):
        os.chdir(self.testArea)
        subprocess.call(["/usr/bin/git", "init"])
        with open(self.testArea + "/something.yaml", "w") as test_file:
            test_file.write(
                """\
- hello.world:
    state: True
    test: 'passing'
"""
            )
        subprocess.call(["/usr/bin/git", "add", "*"])
        subprocess.call(["/usr/bin/git", "commit", "-m", "testing"])
        subprocess.call(["/usr/bin/git", "tag", "TEST_VER"])
        assert (
            self.obj.parse_yaml_version(
                self.testArea + "/something.yaml", "/tmp/work/", self.testArea
            )
            == "TEST_VER"
        )


class TestParseRedirectTable(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir("/tmp/redirector")
        except OSError:
            pass
        self.testArea = "/tmp/redirector/testpath-" + floor(time.time()).__repr__()[:-2]
        os.mkdir(self.testArea)
        self.cwd = os.getcwd()
        with open(self.testArea + "/redirect_table", "w") as table:
            table.writelines(
                [
                    "TS01I-EA-IOC-01 anyarbitrarystringhere\n",
                    "TS01I-gui thisshouldntmatchourregexp\n",
                    "ME99P-XX-IOC-99 butthisoneshould\n",
                    "TS01I-TS-IOC-69 foobarbaz\n",
                    "TS01J-XY-IOC-07 splat\n",
                    "TS10I-AB-IOC-01 bang\n",
                ]
            )

    def tearDown(self):
        os.chdir(self.cwd)
        subprocess.call(["rm", "-rf", self.testArea])
        os.rmdir("/tmp/redirector")

    def test_parse(self):
        list0 = redirector_iocs(
            "", "TS01I-ML-TEST", self.testArea + "/redirect_table"
        ).value.split(" ")[:-1]
        list1 = redirector_iocs(
            "", "ME99P-ML-TEST", self.testArea + "/redirect_table"
        ).value.split(" ")[:-1]
        assert len(list0) == 2
        assert list0[0] == "TS01I-EA-IOC-01"
        assert list0[1] == "TS01I-TS-IOC-69"
        assert len(list1) == 1
        assert list1[0] == "ME99P-XX-IOC-99"
