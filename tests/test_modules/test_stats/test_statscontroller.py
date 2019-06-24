import unittest

from malcolm.core import Process
from malcolm.modules.stats.controllers import StatsController, \
    parse_yaml_version

from malcolm.version import __version__
from cothread import catools
import time
import os
import subprocess
from math import floor


class TestBasicController(unittest.TestCase):
    prefix = "unitTest:%s" % floor(time.time()).__repr__()[:-2]

    def setUp(self):
        self.process = Process("proc")
        self.o = StatsController("MyMRI", prefix=self.prefix)
        self.process.add_controller(self.o)
        self.process.start()
        self.b = self.process.block_view("MyMRI")

    def tearDown(self):
        self.process.stop(timeout=2)

    def test_sets_stats(self):
        assert self.b.pymalcolmVer.value == __version__
        hostname = os.uname()[1]
        hostname = hostname if len(hostname) < 39 else hostname[:35] + '...'
        assert self.b.hostname.value == hostname

    def test_starts_ioc(self):
        assert catools.caget(self.prefix + ":PYMALCOLM:VER") == __version__

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
        self.testArea = '/tmp/prod/testpath-%s' % floor(time.time()).__repr__()[:-2]
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
