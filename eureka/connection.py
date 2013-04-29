# Author: Jeff Vogelsang <jeffvogelsang@gmail.com>
# Copyright 2013 Jeff Vogelsang
#
# Author: Mike Babineau <michael.babineau@gmail.com>
# Copyright 2011 Electronic Arts Inc.
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
import requests
from device import LogglyDevice
from input import LogglyInput
from response import LogglyResponse


class LogglyConnection(object):

    def __init__(self, username=None, password=None, domain=None):

        # Use environment variables for credentials if set.
        if None not in (os.environ.get('LOGGLY_DOMAIN'),
                        os.environ.get('LOGGLY_USERNAME'),
                        os.environ.get('LOGGLY_PASSWORD')):
            self.base_url = 'http://%s/api' % os.environ.get('LOGGLY_DOMAIN')
            self.username = os.environ.get('LOGGLY_USERNAME')
            self.password = os.environ.get('LOGGLY_PASSWORD')

        # Override if credentials passed to constructor.
        if None not in (username, password, domain):
            self.username = username
            self.password = password
            self.base_url = 'http://%s/api' % domain

        # Raise error if we haven't managed to set the credentials at this point.
        if None in (getattr(self, 'username', None),
                    getattr(self, 'password', None),
                    getattr(self, 'base_url', None)):
            raise AttributeError("No Loggly credentials provided or found in environment.")

        # Authentication tuple for requests
        self.auth = (self.username, self.password)

    def __repr__(self):
        return "Connection:%s@%s" % (self.username, self.base_url)

    def _loggly_get(self, path):
        """Given a path, perform a get request using configured base_url and authentication."""

        response = requests.get("%s/%s" % (self.base_url, path), auth=self.auth)

        return LogglyResponse(response)

    def _loggly_post(self, path, data=None):
        """Given a path, perform a post request using configured base_url and authentication.

            If a dictionary containing post data provided send that with the post.
        """

        if data is None:
            response = requests.post("%s/%s" % (self.base_url, path), auth=self.auth)
        else:
            response = requests.post("%s/%s" % (self.base_url, path), data=data, auth=self.auth)

        return LogglyResponse(response)

    def _loggly_delete(self, path):
        """Given a path, perform a delete request using configured base_url and authentication."""

        response = requests.delete("%s/%s" % (self.base_url, path), auth=self.auth)

        return LogglyResponse(response)

    def get_all_inputs(self, input_names=None):
        """Get all inputs, or the specific inputs matching the supplied list of input names."""

        path = 'inputs/'

        response = self._loggly_get(path)

        json = response.json()
        loggly_inputs = []
        if input_names:
            for input_name in input_names:
                loggly_inputs += [LogglyInput(j) for j in json if j['name'] == input_name]
        else:
            loggly_inputs += [LogglyInput(j) for j in json]

        return loggly_inputs

    def get_input(self, input_id):
        """Get a specific input given its id."""

        path = 'inputs/%s/' % input_id

        response = self._loggly_get(path)

        json = response.json()
        loggly_input = LogglyInput(json)

        return loggly_input

    def list_inputs(self):
        """List all inputs."""

        loggly_inputs = self.get_all_inputs()

        input_list = [i.name for i in loggly_inputs]

        return input_list

    def create_input(self, name, service, description=None):
        """Create a new input given a name, service type, and optional description."""

        if not description: description = name

        path = 'inputs/'
        data = {'name': name, 'description': description, 'service': service}

        response = self._loggly_post(path, data)

        json = response.json()
        loggly_input = LogglyInput(json)

        return loggly_input

    def delete_input(self, loggly_input):
        """Delete the given input."""

        path = 'inputs/%s/' % loggly_input.id

        response = self._loggly_delete(path)

        return "%s:%s" % (response.status_code, response.text)

    def get_all_devices(self, device_names=None):
        """Get all devices, or the specific devices matching the supplied list of device names."""

        path = 'devices/'

        response = self._loggly_get(path)

        json = response.json()
        loggly_devices = []
        if device_names:
            for device_name in device_names:
                loggly_devices += [LogglyDevice(j) for j in json if j['ip'] == device_name]
        else:
            loggly_devices += [LogglyDevice(j) for j in json]

        return loggly_devices

    def get_device(self, device_id):
        """Get a specific device given its id."""

        path = 'devices/%s/' % device_id

        response = self._loggly_get(path)

        json = response.json()
        loggly_device = LogglyDevice(json)

        return loggly_device

    def list_devices(self):
        """List all devices."""

        loggly_devices = self.get_all_devices()

        device_list = [i.name for i in loggly_devices]

        return device_list

    def add_device_to_input(self, loggly_device, loggly_input):
        """Add an arbitrary device (specified IP address) to the given input."""

        path = 'devices/'

        data = {'input_id': loggly_input.id, 'ip': loggly_device.ip}

        response = self._loggly_post(path, data)

        json = response.json()
        loggly_device = LogglyDevice(json)

        return loggly_device

    def add_this_device_to_input(self, loggly_input):
        """Add a device matching the IP of the HTTP client calling the API from the given input."""

        path = 'inputs/%s/adddevice/' % loggly_input.id

        response = self._loggly_post(path)

        json = response.json()
        loggly_device = LogglyDevice(json)

        return loggly_device

    def remove_this_device_from_input(self, loggly_input):
        """Remove the device matching the IP of the HTTP client calling the API from the given input."""

        path = 'inputs/%s/removedevice/' % loggly_input.id

        response = self._loggly_delete(path)

        return "%s:%s" % (response.status_code, response.text)

    def delete_device(self, loggly_device):
        """Remove the specified device.

        Note: This removes a device from all inputs. Compare with remove_this_device_from_input.
        """

        path = 'devices/%s/' % loggly_device.id

        response = self._loggly_delete(path)

        return "%s:%s" % (response.status_code, response.text)
