import unittest

from malcolm.core import Process
from malcolm.modules.builtin.controllers import StatefulController
from malcolm.modules.stats.parts import StatsPart, \
    parse_yaml_version

from cothread import catools
import time
import os
import subprocess
from math import floor

from malcolm.version import __version__


class TestStatsPart(unittest.TestCase):
    prefix = "unitTest:%s" % floor(time.time()).__repr__()[:-2]

    def setUp(self):
        self.process = Process("proc")
        self.o = StatefulController("MyMRI")
        self.o.add_part(StatsPart("stats", "MyMRI", prefix=self.prefix))
        self.process.add_controller(self.o)
        self.process.start()
        self.b = self.process.block_view("MyMRI")

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_sets_stats(self):
        # In unit tests, this depends on where the test-runner is run from
        assert self.b.pymalcolmVer.value in ["Work", __version__]
        hostname = os.uname()[1]
        hostname = hostname if len(hostname) < 39 else hostname[:35] + '...'
        assert self.b.hostname.value == hostname

    def test_starts_ioc(self):
        assert catools.caget(self.prefix + ":PYMALCOLM:VER") in ["Work",
                                                                 __version__]

    def test_ioc_ticks(self):
        uptime = catools.caget(self.prefix + ":UPTIME:RAW")
        assert uptime >= 0
        time.sleep(5)
        assert catools.caget(self.prefix + ":UPTIME:RAW") >= uptime + 5


class TestParseYamlVersion(unittest.TestCase):
    def setUp(self):
        try:
            os.mkdir('/tmp/prod')
        except OSError:
            pass
        self.testArea = '/tmp/prod/testpath-' + \
                        floor(time.time()).__repr__()[:-2]
        os.mkdir(self.testArea)
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)
        subprocess.call(['rm', '-rf', self.testArea])
        os.rmdir('/tmp/prod')

    def test_simple_path_parse(self):
        assert parse_yaml_version('/not/work/or/prod/something.yaml',
                                  '/tmp/work/',
                                  '/tmp/prod') == 'unknown'
        assert parse_yaml_version('/tmp/work/something.yaml', '/tmp/work/',
                                  '/tmp/prod') == 'Work'
        assert parse_yaml_version(self.testArea + '/something.yaml',
                                  '/tmp/work/',
                                  self.testArea) == 'Prod (unknown version)'

    def test_git_tag_parse(self):
        os.chdir(self.testArea)
        subprocess.call(['/usr/bin/git', 'init'])
        with open(self.testArea + '/something.yaml', 'w') as test_file:
            test_file.write('''\
- hello.world:
    state: True
    test: 'passing'
''')
        subprocess.call(['/usr/bin/git', 'add', '*'])
        subprocess.call(['/usr/bin/git', 'commit', '-m', 'testing'])
        subprocess.call(['/usr/bin/git', 'tag', 'TEST_VER'])
        assert parse_yaml_version(self.testArea + '/something.yaml',
                                  '/tmp/work/',
                                  self.testArea) == 'TEST_VER'
