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
import json


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

    #### SOURCE MANAGEMENT API ####

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

    def create_input(self, name, service, input_format=None, description=None):
        """Create a new input given a name, service type, and optional description."""

        if not description: description = name

        # Note: Format is only relevant for HTTP sources.
        #       If format is omitted (none), Loggly defaults to text as the format.
        path = 'inputs/'
        data = {'name': name, 'service': service, 'format': input_format, 'description': description}

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

    #### SUBMISSION API ####

    def _submit_data(self, input_key, data, data_type="text"):
        """Submit data to input defined by input_key.

        Note: While this is similar _loggly_post(), it goes to a different URL and has different
              requirements for headers. Thus it has its own function.
        """

        # The content-type header differentiates between text and json. Text is the default.
        if data_type == "json":
            headers = {'content-type': 'application/x-www-form-urlencoded'}
        else:
            headers = {'content-type': 'text/plain'}

        # Note that the URL for HTTP inputs is the same for all customers...
        url = "https://logs.loggly.com/inputs/%s" % input_key

        response = requests.post(url, data=data, headers=headers, auth=self.auth)

        return LogglyResponse(response)

    def submit_text_data(self, text_data, input_key):
        """Submit plain text data to HTTP input identified by input_key."""

        #TODO Write test for verifying submission after we can get data out.

        response = self._submit_data(input_key, text_data)

        return "%s:%s" % (response.status_code, response.text)

    def submit_json_data(self, json_data, input_key):
        """Submit JSON formatted data to HTTP input identified by input_key."""

        #TODO Write test for verifying submission after we can get data out.

        response = self._submit_data(input_key, json_data, "json")

        return "%s:%s" % (response.status_code, response.text)

    #### RETRIEVAL API ####

    # Standard Queries

    def _search_events(self, query_string, rows=None, start=None, from_date=None, until_date=None,
                       order=None, callback=None, output_format=None, fields=None):
        """Assemble Loggly API request for searching events data and returning results."""

        query_params = {
            'q': query_string
        }

        if rows is not None:
            query_params['rows'] = rows
        if start is not None:
            query_params['start'] = start
        if from_date is not None:
            query_params['from'] = from_date
        if until_date is not None:
            query_params['until'] = until_date
        if order is not None:
            query_params['order'] = order
        if callback is not None:
            query_params['callback'] = callback
        if output_format is not None:
            query_params['format'] = output_format
        if fields is not None:
            query_params['fields'] = fields

        path = "search?"

        for param in query_params:
            path = path + param + "=" + query_params[param] + "&"
        path = path.rstrip("&")  # remove extra &

        response = requests.get("%s/%s" % (self.base_url, path), auth=self.auth)

        return LogglyResponse(response)

    #TODO Write tests for verifying retrievals utilizing submissions.

    def get_events(self, query_string, **kwargs):
        """Return events matching query_string."""

        response = self._search_events(query_string, **kwargs)

        return response.text

    def get_events_json(self, query_string, **kwargs):
        """Return events matching query_string as (raw) JSON."""

        response = self._search_events(query_string, output_format="json", **kwargs)

        return response.text

    def get_events_dict(self, query_string, **kwargs):
        """Return events matching query_string as a Python dictionary."""

        return json.loads(self.get_events_json(query_string, **kwargs))

    def get_events_xml(self, query_string, **kwargs):
        """Return events matching query_string as XML."""

        response = self._search_events(query_string, output_format="xml", **kwargs)

        return response.text

    def get_events_text(self, query_string, **kwargs):
        """Return events matching query_string as Text."""

        response = self._search_events(query_string, output_format="text", **kwargs)

        return response.text

    # Faceted Queries

    def _search_events_faceted(self, facetby, query_string, from_date=None, until_date=None, buckets=None,
                               gap=None, callback=None, output_format=None):

        query_params = {
            'q': query_string
        }

        if from_date is not None:
            query_params['from'] = from_date
        if until_date is not None:
            query_params['until'] = until_date
        if buckets is not None:
            query_params['buckets'] = buckets
        if gap is not None:
            query_params['gap'] = gap
        if callback is not None:
            query_params['callback'] = callback
        if output_format is not None:
            query_params['format'] = output_format

        path = "facets/%s/?" % facetby

        for param in query_params:
            path = path + param + "=" + query_params[param] + "&"
        path = path.rstrip("&")  # remove extra &

        response = requests.get("%s/%s" % (self.base_url, path), auth=self.auth)

        return LogglyResponse(response)

    def get_events_faceted(self, facetby, query_string, **kwargs):
        """Return faceted events matching query_string."""

        response = self._search_events_faceted(facetby, query_string, **kwargs)

        return response.text

    def get_events_faceted_json(self, facetby, query_string, **kwargs):
        """Return faceted events matching query_string as JSON."""

        response = self._search_events_faceted(facetby, query_string, output_format="json", **kwargs)

        return response.text

    def get_events_faceted_dict(self, facetby, query_string, **kwargs):
        """Return faceted events matching query_string as a Python dictionary."""

        return json.loads(self.get_events_faceted_json(facetby, query_string, **kwargs))

    def get_events_faceted_xml(self, facetby, query_string, output_format="xml", **kwargs):
        """Return faceted events matching query_string as XML."""

        response = self._search_events_faceted(facetby, query_string, **kwargs)

        return response.text

    def get_events_faceted_text(self, facetby, query_string, **kwargs):
        """Return faceted events matching query_string as Text."""

        response = self._search_events_faceted(facetby, query_string, output_format="text", **kwargs)

        return response.text