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
import json
import string
import unittest
import time
from eureka import connect_loggly
from connection import LogglyDevice

# Ensure that live test only run if LOGGLY_TEST_LIVE variable is present in the environment and set to 'True'
# Note: Live tests are designed to reasonably safely create and destroy Loggly inventory without affecting
#       existing configuration through use of randomized strings and loop-back IP addresses.
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
        self.env_password_save = os.environ.get('LOGGLY_PASSWORD')
        self.env_domain_save = os.environ.get('LOGGLY_DOMAIN')
        self.env_protocol_save = os.environ.get('LOGGLY_PROTOCOL')

    def tearDown(self):

        def restore_environment(env_var, env_var_saved):

            if env_var_saved is not None:
                os.environ[env_var] = env_var_saved
            else:
                if os.environ.get(env_var) is not None:
                    del os.environ[env_var]

        restore_environment('LOGGLY_USERNAME', self.env_username_save)
        restore_environment('LOGGLY_PASSWORD', self.env_password_save)
        restore_environment('LOGGLY_DOMAIN', self.env_domain_save)
        restore_environment('LOGGLY_PROTOCOL', self.env_protocol_save)

    def testConnCredsFromEnv(self):

        os.environ['LOGGLY_USERNAME'] = 'env_username'
        os.environ['LOGGLY_PASSWORD'] = 'env_password'
        os.environ['LOGGLY_DOMAIN'] = 'env_domain'

        conn = connect_loggly()

        self.assertEquals('env_username', getattr(conn, 'username'))
        self.assertEquals('env_password', getattr(conn, 'password'))
        self.assertEquals('https://env_domain/api', getattr(conn, 'base_url'))

        # Make sure we can override the HTTP default.
        os.environ['LOGGLY_PROTOCOL'] = 'http'

        conn = connect_loggly()
        self.assertEquals('http', getattr(conn, 'protocol'))
        self.assertEquals('http://env_domain/api', getattr(conn, 'base_url'))

    def testConnCredsSupplied(self):

        conn = connect_loggly('username', 'password', 'domain')

        self.assertEquals('username', getattr(conn, 'username'))
        self.assertEquals('password', getattr(conn, 'password'))
        self.assertEquals('https://domain/api', getattr(conn, 'base_url'))

        conn = connect_loggly('username', 'password', 'domain', 'http')
        self.assertEquals('http', getattr(conn, 'protocol'))
        self.assertEquals('http://domain/api', getattr(conn, 'base_url'))

    def testConnCredsMissing(self):

        if os.environ.get('LOGGLY_USERNAME') is not None:
            del os.environ['LOGGLY_USERNAME']
        if os.environ.get('LOGGLY_PASSWORD') is not None:
            del os.environ['LOGGLY_PASSWORD']
        if os.environ.get('LOGGLY_DOMAIN') is not None:
            del os.environ['LOGGLY_DOMAIN']

        self.assertRaises(AttributeError, connect_loggly)

    def testConnRepr(self):

        os.environ['LOGGLY_USERNAME'] = 'env_username'
        os.environ['LOGGLY_PASSWORD'] = 'env_password'
        os.environ['LOGGLY_DOMAIN'] = 'env_domain'

        # Credentials from enviornment
        conn = connect_loggly()
        self.assertEqual("Connection:env_username@https://env_domain/api", "%s" % conn)

        del os.environ['LOGGLY_USERNAME']
        del os.environ['LOGGLY_PASSWORD']
        del os.environ['LOGGLY_DOMAIN']

        # Credentials supplied to constructor
        conn = connect_loggly('username', 'password', 'domain')
        self.assertEqual("Connection:username@https://domain/api", "%s" % conn)


@unittest.skipIf(not enable_live_tests, 'Live connection tests skipped.')
class TestLogglyLive(unittest.TestCase):
    """Live tests. Prove code works against live API.

    Note: As these are live tests, running an integration-level, they are subject to environmental failures!
          If you experience a failure, the tests may leave behind inputs and devices you'll want to clean up.
    """

    def setUp(self):
        """Re-use a live connection to loggly for tests."""

        self.conn = connect_loggly()

        print "Using: %s" % self.conn

    # Helper methods

    def _create_input(self, input_type="syslogudp", input_format="text"):
        """Create and with a randomized name and description for testing purposes."""

        input_name = "test-input-%s" % rand_string()
        input_desc = "test-description-%s" % rand_string()

        loggly_input = self.conn.create_input(input_name, input_type, input_format, input_desc)

        print "Created input: %s, %s" % (loggly_input.id, loggly_input.name)
        return loggly_input

    def _create_syslog_input(self):
        """Create a syslog input with a randomized named and description for testing purposes."""

        return self._create_input(input_type="syslogudp")

    def _create_http_text_input(self):
        """Create a http text input with a randomized named and description for testing purposes."""

        return self._create_input(input_type="http")

    def _create_http_json_input(self):
        """Create a http json input with a randomized named and description for testing purposes."""

        return self._create_input(input_type="http", input_format="json")

    def _get_events(self, test_faceted=False, test_json=False):
        """Local method for testing retrieval methods: Facedted vs. not, JSON vs. not."""

        submit_attempts = 10  # number of times to attempt submitting an event.
        submit_attempt_delay = 30  # delay between attempts in seconds

        search_attempts = 10  # number of times to attempt searching for an event.
        search_attempt_delay = 30  # delay between attempts in seconds

        # Create an input. Need an HTTP input.
        if test_json:
            loggly_input = self._create_http_json_input()
        else:
            loggly_input = self._create_http_text_input()

        # Make a random string that we're certain won't be found.
        event_string = rand_string(150)
        if test_json:
            event = json.dumps({
                'event_string': event_string
            })
        else:
            event = event_string

        # Test submitting a event.
        event_submitted = False
        while not event_submitted and submit_attempts > 0:
            try:
                self.conn.submit_text_data(event, loggly_input.input_token)
                print "Event submitted."
                event_submitted = True
            except Exception as e:
                submit_attempts -= 1
                print "Error submitting event: %s" % e.message
                print "%s tries left. Will try again in %s seconds." % (submit_attempts, submit_attempt_delay)
                time.sleep(submit_attempt_delay)

        self.assertTrue(event_submitted, "Event not submitted.")

        # Test retrieving event.
        event_found = False
        while not event_found and search_attempts > 0:
            try:
                if test_faceted:
                    if test_json:
                        print "Testing faceted JSON search."
                        events = self.conn.get_events_faceted_dict('date', 'json.event_string:"%s"' % event_string)
                    else:
                        print "Testing faceted Text search."
                        events = self.conn.get_events_faceted_dict('date', event_string)
                else:
                    if test_json:
                        print "Testing JSON search."
                        events = self.conn.get_events_dict('json.event_string:"%s"' % event_string)
                    else:
                        print "Testing Text search."
                        events = self.conn.get_events_dict(event_string)
                num_found = events['numFound']
                if num_found > 0:
                    print "Event found."
                    event_found = True
                else:
                    search_attempts -= 1
                    print "Event not found. %s tries left. Will try again in %s seconds." \
                          % (search_attempts, search_attempt_delay)
                    time.sleep(search_attempt_delay)
            except Exception as e:
                search_attempts -= 1
                print "Error searching for event: %s" % e.message
                print "%s tries left. Will try again in %s seconds." % (search_attempts, search_attempt_delay)

        self.assertTrue(event_found, "Event not found.")

        # Remove the input
        self.conn.delete_input(loggly_input)

    # Tests

    def testCreateDeleteInput(self):
        """Create an input then delete it."""

        loggly_input = self._create_syslog_input()
        self.conn.delete_input(loggly_input)

    def testCreateDeleteDevice(self):
        """Create a device then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self._create_syslog_input()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device = self.conn.add_device_to_input(min_loggly_device, loggly_input)  # create actual device

        self.conn.delete_device(loggly_device)
        self.conn.delete_input(loggly_input)

    def testCreateDeleteDeviceWithName(self):
        """Create a device then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self._create_syslog_input()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()})
        loggly_device = self.conn.add_device_to_input(min_loggly_device, loggly_input, "test-name-%s" % rand_string())

        self.conn.delete_device(loggly_device)
        self.conn.delete_input(loggly_input)

    def testCreateDeleteDeviceWithIP(self):
        """Create a device using an IP and Name, then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self._create_syslog_input()

        device_ip = get_rand_private_ip()
        device_name = "test-name-%s" % rand_string()

        loggly_device = self.conn.add_ip_to_input(device_ip, loggly_input, device_name)  # create actual device

        self.conn.delete_device(loggly_device)
        self.conn.delete_input(loggly_input)

    def testCreateDeleteDeviceWithIPAndNamedInput(self):
        """Create a device using an IP and Name, then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self._create_syslog_input()

        device_ip = get_rand_private_ip()
        device_name = "test-name-%s" % rand_string()

        loggly_device = self.conn.add_ip_to_input_by_name(device_ip, loggly_input.name, device_name)

        self.conn.delete_device(loggly_device)
        self.conn.delete_input(loggly_input)

    def testCreateDeleteThisDevice(self):
        """Create a device based on the current IP that Loggly sees, then delete it.

        This requires adding the device to an input, so we create and delete one of these as well.
        """

        loggly_input = self._create_syslog_input()

        loggly_device = self.conn.add_this_device_to_input(loggly_input)

        self.conn.remove_this_device_from_input(loggly_input)
        self.conn.delete_device(loggly_device)

    def testGetAllInputs(self):
        """Get all inputs.

        To make sure we're getting multiple inputs, create a few, get the list, then delete them.
        """
        loggly_input1 = self._create_syslog_input()
        loggly_input2 = self._create_syslog_input()

        inputs = self.conn.get_all_inputs()
        self.assertGreaterEqual(len(inputs), 2)

        self.conn.delete_input(loggly_input1)
        self.conn.delete_input(loggly_input2)

    def testGetInputFromGetAllInputs(self):
        """Use get all inputs to get a specific input by name.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input1 = self._create_syslog_input()
        loggly_input2 = self._create_syslog_input()

        self.assertEqual(1, len(self.conn.get_all_inputs([loggly_input1.name])))
        self.assertEqual(loggly_input1.id, self.conn.get_all_inputs([loggly_input1.name])[0].id)

        self.assertEqual(2, len(self.conn.get_all_inputs([loggly_input1.name, loggly_input2.name])))

        self.conn.delete_input(loggly_input1)
        self.conn.delete_input(loggly_input2)

    def testGetInputByName(self):
        """Create an input, and then find its ID using the input's name.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input_to_find = self._create_syslog_input()
        loggly_input_found = self.conn.get_input_by_name(loggly_input_to_find.name)

        self.assertEqual(loggly_input_found.id, loggly_input_to_find.id)

        self.conn.delete_input(loggly_input_to_find)

    def testGetInputByNameNotFoundErrors(self):
        """Ensure we get an exception if we search for an input that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_input_by_name, rand_string(32))

    def testGetInputIdByName(self):
        """Create an input, and then find its ID using the input's name.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input_to_find = self._create_syslog_input()
        loggly_input_found_id = self.conn.get_input_id_by_name(loggly_input_to_find.name)

        self.assertEqual(loggly_input_found_id, loggly_input_to_find.id)

        self.conn.delete_input(loggly_input_to_find)

    def testGetInputIdByNameNotFoundErrors(self):
        """Ensure we get an exception if we search for an input that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_input_id_by_name, rand_string(32))

    def testGetInput(self):
        """Get a single input by id.

        We create a input so we can test finding a specific input, then delete it.
        """

        loggly_input_to_find = self._create_syslog_input()
        loggly_input_found = self.conn.get_input(loggly_input_to_find.id)

        self.assertEqual(loggly_input_found.id, loggly_input_to_find.id)

        self.conn.delete_input(loggly_input_found)

    def testGetAllDevices(self):
        """Get all devices.

        To make sure we're getting multiple devices, create a few attached to a new input, get the list,
          then delete the input and the devices.
        """

        loggly_input = self._create_syslog_input()

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

        loggly_input = self._create_syslog_input()

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

        loggly_input = self._create_syslog_input()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input) # create actual devices

        loggly_device_found = self.conn.get_device(loggly_device_to_find.id)
        self.assertEqual(loggly_device_found.id, loggly_device_to_find.id)

        self.conn.delete_device(loggly_device_found)
        self.conn.delete_input(loggly_input)

    def testGetDeviceByName(self):
        """Create an device, and then find it using the device's name.

        We create a device so we can test finding a specific device, then delete it.
        """

        loggly_input = self._create_syslog_input()

        device_name = "test-name-%s" % rand_string()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input, device_name)

        loggly_device_found = self.conn.get_device_by_name(device_name)

        self.assertEqual(loggly_device_to_find.id, loggly_device_found.id)

        self.conn.delete_device(loggly_device_to_find)
        self.conn.delete_input(loggly_input)

    def testGetDeviceByNameNotFound(self):
        """Ensure we get an exception if we search for a device that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_device_by_name, rand_string(32))

    def testGetDeviceIdByName(self):
        """Create an device, and then find its ID using the device's name.

        We create a device so we can test finding a specific device, then delete it.
        """

        loggly_input = self._create_syslog_input()

        device_name = "test-name-%s" % rand_string()

        min_loggly_device = LogglyDevice({'ip': get_rand_private_ip()}) # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input, device_name)

        loggly_device_found_id = self.conn.get_device_id_by_name(device_name)

        self.assertEqual(loggly_device_to_find.id, loggly_device_found_id)

        self.conn.delete_device(loggly_device_to_find)
        self.conn.delete_input(loggly_input)

    def testGetDeviceIdByNameNotFound(self):
        """Ensure we get an exception if we search for a device that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_device_id_by_name, rand_string(32))

    def testGetDeviceByIp(self):
        """Create an device, and then find it using the device's name.

        We create a device so we can test finding a specific device, then delete it.
        """

        loggly_input = self._create_syslog_input()

        device_ip = get_rand_private_ip()

        min_loggly_device = LogglyDevice({'ip': device_ip})  # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input)

        loggly_device_found = self.conn.get_device_by_ip(device_ip)

        self.assertEqual(loggly_device_to_find.id, loggly_device_found.id)

        self.conn.delete_device(loggly_device_to_find)
        self.conn.delete_input(loggly_input)

    def testGetDeviceByIpNotFound(self):
        """Ensure we get an exception if we search for a device that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_device_by_ip, get_rand_private_ip())

    def testGetDeviceIdByIp(self):
        """Create an device, and then find its ID using the device's name.

        We create a device so we can test finding a specific device, then delete it.
        """

        loggly_input = self._create_syslog_input()

        device_ip = get_rand_private_ip()

        min_loggly_device = LogglyDevice({'ip': device_ip})  # de minimus Loggly device
        loggly_device_to_find = self.conn.add_device_to_input(min_loggly_device, loggly_input)

        loggly_device_found_id = self.conn.get_device_id_by_ip(device_ip)

        self.assertEqual(loggly_device_to_find.id, loggly_device_found_id)

        self.conn.delete_device(loggly_device_to_find)
        self.conn.delete_input(loggly_input)

    def testGetDeviceIdByIpNotFound(self):
        """Ensure we get an exception if we search for a device that doesn't exist.

        """

        self.assertRaises(Exception, self.conn.get_device_id_by_ip, get_rand_private_ip())

    def testSubmitAndRetrieveTextEvents(self):
        """Test submitting and retrieving Text events."""

        self._get_events(test_faceted=False, test_json=False)

    def testSubmitAndRetrieveJsonEvents(self):
        """Test submitting and retrieving JSON events."""

        self._get_events(test_faceted=False, test_json=True)

    def testSubmitAndRetrieveTextEventsFaceted(self):
        """Test submitting and retrieving faceted Text events."""

        self._get_events(test_faceted=True, test_json=False)

    def testSubmitAndRetrieveJsonEventsFaceted(self):
        """Test submitting and retrieving faceted JSON events."""

        self._get_events(test_faceted=True, test_json=True)

    def testLogglyExceptions(self):

        # A device with an 12-character string id should cause a 400 status code and raise and exception.
        bad_device = LogglyDevice({'id': rand_string()})

        self.assertRaises(Exception, self.conn.delete_device, bad_device)


if __name__ == '__main__':

    unittest.main(verbosity=2)