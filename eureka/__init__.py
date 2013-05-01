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

from connection import LogglyConnection

__version__ = '0.10'

__author__ = 'Jeff Vogelsang <jeffvogelsang@gmail.com>'
__copyright__ = "Jeff Vogelsang"
__license__ = "Apache v2.0"


def connect_loggly(username=None, password=None, domain=None, protocol="https"):
    """Get a Loggly connection."""

    # Note: connect_loggly assumes HTTPS.

    return LogglyConnection(username, password, domain, protocol)
