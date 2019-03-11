import pytest
from mock import call, MagicMock
import os
from datetime import datetime

from scanpointgenerator import LineGenerator, CompoundGenerator
from malcolm.core import Context, Process
from malcolm.modules.ADOdin.parts import OdinWriterPart
from malcolm.modules.ADOdin.blocks import odin_writer_block
from malcolm.testutil import ChildTestCase


class TestOdinDWriterPart(ChildTestCase):

    def setUp(self):
        self.process = Process("Process")
        self.context = Context(self.process)
        self.child = self.create_child_block(
            odin_writer_block, self.process,
            mri="mri", prefix="prefix")
        self.set_attributes(self.child,
                            numProcesses=4)
        self.o = OdinWriterPart(name="m", mri="mri")
        self.context.set_notify_dispatch_request(self.o.notify_dispatch_request)
        self.process.start()

        self.completed_steps = 0
        # goal for these is 3000, 2000, True
        cols, rows, alternate = 3000, 2000, False
        self.steps_to_do = cols * rows
        xs = LineGenerator("x", "mm", 0.0, 0.5, cols, alternate=alternate)
        ys = LineGenerator("y", "mm", 0.0, 0.1, rows)
        self.generator = CompoundGenerator([ys, xs], [], [], 0.1)
        self.generator.prepare()

    def tearDown(self):
        self.process.stop(timeout=1)

    def test_configure(self):
        # the test makes /tmp/odin.hdf - make sure a previous one is not there
        vds_file = os.path.join('/tmp', 'odin.hdf')
        if os.path.exists(vds_file):
            os.remove(vds_file)
        # also the VDS will look for the existence of these files:
        for i in range(1, 5):
            # todo this is a bug since these files wont be created
            #  in normal conditions. Need to get vdsgen to cope with this
            #  in some fashion
            # todo ALSO need to get vdsgen to cope with 6 million points
            #  this will require spawning to another process methinks
            open(os.path.join(
                '/tmp', 'odin_raw_data{}.hdf'.format(i)), 'w'
            ).close()

        start_time = datetime.now()
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do,
            generator=self.generator, fileDir='/tmp', fileName='odin.hdf')
        assert self.child.handled_requests.mock_calls == [
            call.put('fileName', 'odin_raw_data.hdf'),
            call.put('filePath', '/tmp/'),
            call.put('numCapture', self.steps_to_do),
            call.post('start')]
        print(self.child.handled_requests.mock_calls)
        print('OdinWriter configure {} points took {} secs'.format(
            self.steps_to_do, datetime.now() - start_time))

    def test_run(self):
        self.o.configure(
            self.context, self.completed_steps, self.steps_to_do,
            generator=self.generator, fileDir='/tmp', fileName='odin.hdf')
        self.child.handled_requests.reset_mock()
        self.o.registrar = MagicMock()
        # run waits for this value
        self.child.field_registry.get_field("numCaptured").set_value(
            self.o.done_when_reaches)
        self.o.run(self.context)
        assert self.child.handled_requests.mock_calls == [
            call.when_values_matches(
                'numCaptured', self.steps_to_do, None, None, 60)]
        assert self.o.registrar.report.called_once
        assert self.o.registrar.report.call_args_list[0][0][0].steps == \
               self.steps_to_do
