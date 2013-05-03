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

from error import LogglyException


class LogglyResponse(object):
    """Wrapper for the requests package response object.

    Provides a mechanism for injecting Loggly-specific response information,
    and handling response status_codes from Loggly that are considered errors.
    """

    # Loggly-specific response codes to API-calls. See: http://loggly.com/support/advanced/api-manage-sources/
    _status_codes = {200: {'message': 'OK',
                           'description': 'Indicates that the request was successful.'},
                     201: {'message': 'Created',
                           'description': 'The object was successfully created. This is for a POST call.'},
                     204: {'message': 'Deleted',
                           'description': 'The object was deleted. This pertains to DELETE calls.'},
                     400: {'message': 'Bad Request',
                           'description': 'Check your request parameters. You might be using an unsupported '
                                          'parameter or have a malformed something or another.'},
                     401: {'message': 'Unauthorized',
                           'description': 'Either your credentials specified were invalid.'},
                     403: {'message': 'Forbidden',
                           'description': 'User does not have privileges to execute the action.'},
                     404: {'message': 'Not Found',
                           'description': 'The resource you have referenced could not be found.'},
                     409: {'message': 'Conflict/Duplicate',
                           'description': 'There was some conflict. Most likely you are '
                                          'trying to create a resource that already exists.'},
                     410: {'message': 'Gone',
                           'description': 'You have referenced an object that does not exist.'},
                     500: {'message': 'Internal Server Error',
                           'description': 'There has been an error from which Loggly could not '
                                          'recover. We are likely notified when this happens.'},
                     501: {'message': 'Not Implemented',
                           'description': 'You are trying to access functionality that '
                                          'is not implemented. Yet.'},
                     503: {'message': 'Throttled',
                           'description': 'Like a needy child, you are overloading '
                                          'us with requests for events. Try again later.'}}

    # Codes considered exceptions/failures
    _exception_codes = (400, 401, 403, 404, 409, 410, 500, 501, 503)

    def __init__(self, obj):
        self._wrapped_obj = obj

        # Add Loggly-specific information to response.
        self.loggly_message = self._status_codes[self.status_code]['message']
        self.loggly_description = self._status_codes[self.status_code]['description']
        self.loggly_info = "%s: %s - %s" % (self.status_code, self.loggly_message, self.loggly_description)

        # Handle responses considered to be errors.
        if self.status_code in self._exception_codes:
            raise LogglyException(self.loggly_info)

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._wrapped_obj, attr)

    def __repr__(self):
        # Add Loggly-specific information to representation.
        return "Response: %s" % self.loggly_info