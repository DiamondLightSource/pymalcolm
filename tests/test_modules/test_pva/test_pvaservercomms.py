import unittest

from malcolm.modules.pva.controllers import PvaServerComms


class TestPvaServerComms(unittest.TestCase):

    def setUp(self):
        self.pva_server_comms = PvaServerComms("TEST:COMMS")

    def test_testChannel_returns_True_if_channel_is_in_published(self):
        channel_name = "CHANNEL1"
        self.pva_server_comms._published.add(channel_name)

        self.assertEqual(True, self.pva_server_comms.testChannel(channel_name))

    def test_testChannel_returns_True_if_channel_of_field_is_in_published(self):
        channel_name = "CHANNEL1"
        field = "FIELD1"
        self.pva_server_comms._published.add(channel_name)

        self.assertEqual(True, self.pva_server_comms.testChannel(
            "{channel}.{field}".format(
                channel=channel_name,
                field=field)))

    def test_testChannel_returns_False_if_channel_is_not_in_published(self):
        channel_name = "CHANNEL1"

        self.assertEqual(False, self.pva_server_comms.testChannel(channel_name))

    def test_testChannel_returns_False_if_channel_of_field_is_not_in_published(self):
        channel_name = "CHANNEL1"
        field = "FIELD1"

        self.assertEqual(False, self.pva_server_comms.testChannel(
            "{channel}.{field}".format(
                channel=channel_name,
                field=field)))

    def test_make_channel_raises_NameError_for_bad_channel_name(self):
        channel_name = "CHANNEL1"
        source = "Source1"

        self.assertRaises(
            NameError, self.pva_server_comms._make_channel, channel_name, source)
