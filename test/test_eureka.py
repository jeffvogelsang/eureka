# Author: Jeff Vogelsang <jeffvogelsang@gmail.com>
# Copyright 2013 Jeff Vogelsang
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import random
from random import randrange
import string
import unittest
from eureka import connect_loggly
from connection import LogglyDevice

# Ensure that live test only run LOGGLY_TEST_LIVE is present in the environment and set to 'True'
# Note: Live tests are designed to safely create and destroy Loggly inventory without affecting existing configuration.
enable_live_tests = os.environ.get('LOGGLY_TEST_LIVE')
if enable_live_tests is not None and enable_live_tests == 'True':
    enable_live_tests = True


def rand_string(count=12):
    """Return random string of length count with letters and numbers, mixed case. Uses Python randomness."""

    return ''.join(random.choice(string.ascii_letters + string.digits) for x in range(count))


def get_rand_private_ip():
    """Return a random IP based on the 127.x.x.x block."""

    return "127.%s.%s.%s" % (randrange(0, 255, 1), randrange(0, 255, 1), randrange(0, 255, 1))


class TestLoggly(unittest.TestCase):

    def setUp(self):

        # Preserve environment settings, put them back when done.
        self.env_username_save = os.environ.get('LOGGLY_USERNAME')
        self.env__password = os.environ.get('LOGGLY_PASSWORD')
        self.env_domain = os.environ.get('LOGGLY_DOMAIN')

    def tearDown(self):

        # Restore environment settings.
        if self.env_username_save is not None:
            os.environ['LOGGLY_USERNAME'] = self.env_username_save
        if self.env__password is not None:
            os.environ['LOGGLY_PASSWORD'] = self.env__password
        if self.env_domain is not None:
            os.environ['LOGGLY_DOMAIN'] = self.env_domain

    def testConnCredsFromEnv(self):

        os.environ['LOGGLY_USERNAME'] = 'env_username'
        os.environ['LOGGLY_PASSWORD'] = 'env_password'
        os.environ['LOGGLY_DOMAIN'] = 'env_domain'

        conn = connect_loggly()

        self.assertEquals('env_username', getattr(conn, 'username'))
        self.assertEquals('env_password', getattr(conn, 'password'))
        self.assertEquals('http://env_domain/api', getattr(conn, 'base_url'))

    def testConnCredsSupplied(self):

        conn = connect_loggly('username', 'password', 'domain')

        self.assertEquals('username', getattr(conn, 'username'))
        self.assertEquals('password', getattr(conn, 'password'))
        self.assertEquals('http://domain/api', getattr(conn, 'base_url'))

    def testConnCredsMissing(self):

        del os.environ['LOGGLY_USERNAME']
        del os.environ['LOGGLY_PASSWORD']
        del os.environ['LOGGLY_DOMAIN']

        self.assertRaises(AttributeError, connect_loggly)

    def testConnRepr(self):

        os.environ['LOGGLY_USERNAME'] = 'env_username'
        os.environ['LOGGLY_PASSWORD'] = 'env_password'
        os.environ['LOGGLY_DOMAIN'] = 'env_domain'

        # Credentials from enviornment
        conn = connect_loggly()
        self.assertEqual("Connection:env_username@http://env_domain/api", "%s" % conn)

        del os.environ['LOGGLY_USERNAME']
        del os.environ['LOGGLY_PASSWORD']
        del os.environ['LOGGLY_DOMAIN']

        # Credentials supplied to constructor
        conn = connect_loggly('username', 'password', 'domain')
        self.assertEqual("Connection:username@http://domain/api", "%s" % conn)


@unittest.skipIf(not enable_live_tests, 'Live connection tests skipped.')
class TestLogglyLive(unittest.TestCase):

    def setUp(self):
        """Re-use a live connection to loggly for tests."""

        self.conn = connect_loggly()

    def create_input(self):
        """Create an input with a randomize name and description."""

        input_name = "test-input-%s" % rand_string()
        input_desc = "test-description-%s" % rand_string()
        loggly_input = self.conn.create_input(input_name, 'syslogudp', input_desc)
        print "Created input: %s, %s" % (loggly_input.id, loggly_input.name)
        return loggly_input

    def testCreateDeleteInput(self):
        """Create an input then delete it."""

        loggly_input = self.create_input()
        self.conn.delete_input(loggly_input)

    def testCreateDeleteDevice(self):
        """Create a device then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self.create_input()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device = self.conn.add_device_to_input(min_loggly_device, loggly_input)  # create actual device

        self.conn.delete_device(loggly_device)
        self.conn.delete_input(loggly_input)

    def testCreateDeleteThisDevice(self):
        """Create a device based on the current IP that Loggly sees, then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self.create_input()

        loggly_device = self.conn.add_this_device_to_input(loggly_input)

        self.conn.remove_this_device_from_input(loggly_input)
        self.conn.delete_device(loggly_device)

    def testGetAllInputs(self):
        """Get all inputs.

        To make sure we're getting multiple inputs, create a few, get the list, then delete them.
        """
        loggly_input1 = self.create_input()
        loggly_input2 = self.create_input()

        inputs = self.conn.get_all_inputs()
        self.assertGreaterEqual(len(inputs), 2)

        self.conn.delete_input(loggly_input1)
        self.conn.delete_input(loggly_input2)

    def testGetInputFromGetAllInputs(self):
        """Use get all inputs to get a specific input by name.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input1 = self.create_input()
        loggly_input2 = self.create_input()

        self.assertEqual(1, len(self.conn.get_all_inputs([loggly_input1.name])))
        self.assertEqual(loggly_input1.id, self.conn.get_all_inputs([loggly_input1.name])[0].id)

        self.assertEqual(2, len(self.conn.get_all_inputs([loggly_input1.name, loggly_input2.name])))

        self.conn.delete_input(loggly_input1)
        self.conn.delete_input(loggly_input2)

    def testGetInput(self):
        """Get a single input by id.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input_to_find = self.create_input()
        loggly_input_found = self.conn.get_input(loggly_input_to_find.id)

        self.assertEqual(loggly_input_found.id, loggly_input_to_find.id)

        self.conn.delete_input(loggly_input_found)

    def testGetAllDevices(self):
        """Get all devices.

        To make sure we're getting multiple devices, create a few attached to a new input, get the list,
          then delete the input and the devices.
        """

        loggly_input = self.create_input()

        min_loggly_device1 = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        min_loggly_device2 = LogglyDevice({'ip': get_rand_private_ip()})

        loggly_device1 = self.conn.add_device_to_input(min_loggly_device1, loggly_input) # create actual devices
        loggly_device2 = self.conn.add_device_to_input(min_loggly_device2, loggly_input)

        devices = self.conn.get_all_devices()

        self.assertGreaterEqual(len(devices), 2)

        self.conn.delete_device(loggly_device1)
        self.conn.delete_device(loggly_device2)
        self.conn.delete_input(loggly_input)

    def testGetDeviceFromGetAllDevices(self):
        """Use get all devices to get a specific device by IP.

        We create an input and a device so we can test finding a specific device, then delete them.
        """

        loggly_input = self.create_input()

        min_loggly_device1 = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        min_loggly_device2 = LogglyDevice({'ip': get_rand_private_ip()})

        loggly_device1 = self.conn.add_device_to_input(min_loggly_device1, loggly_input) # create actual devices
        loggly_device2 = self.conn.add_device_to_input(min_loggly_device2, loggly_input)

        self.assertEqual(1, len(self.conn.get_all_devices([loggly_device1.ip])))
        self.assertEqual(loggly_device1.id, self.conn.get_all_devices([loggly_device1.ip])[0].id)

        self.assertEqual(2, len(self.conn.get_all_devices([loggly_device1.ip, loggly_device2.ip])))

        self.conn.delete_device(loggly_device1)
        self.conn.delete_device(loggly_device2)
        self.conn.delete_input(loggly_input)

    def testGetDevice(self):
        """ Get a single device by id.

        We create a device so we can test finding a specific device, then delete it.
        """

        loggly_input = self.create_input()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input) # create actual devices

        loggly_device_found = self.conn.get_device(loggly_device_to_find.id)
        self.assertEqual(loggly_device_found.id, loggly_device_to_find.id)

        self.conn.delete_device(loggly_device_found)
        self.conn.delete_input(loggly_input)

    def testLogglyExceptions(self):

        # A device with an 12-character string id should cause a 400 status code and raise and exception.
        bad_device = LogglyDevice({'id': rand_string()})

        self.assertRaises(Exception, self.conn.delete_device, bad_device)


if __name__ == '__main__':

    unittest.main(verbosity=2)