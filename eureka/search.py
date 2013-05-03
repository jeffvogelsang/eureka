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

import json


class LogglySearch(object):
    """Loggly search object. Makes the results of a Loggly search available as structured data."""

    is_faceted = None
    response = None
    response_payload = None
    context = None
    data = None
    numFound = None
    gmt_offset = None
    gap = None

    def __init__(self, response, is_faceted):

        self.is_faceted = is_faceted

        self.response = response
        self.response_payload = json.loads(response.text)

        for key in self.response_payload.keys():

            if key == 'context':
                self.context = LogglySearchContext(self.response_payload['context'])
            elif key == 'data':
                data = self.response_payload[key]
                self.data = []
                if is_faceted:
                    for key in data:
                        # Facets are structured as the facetby key and the count of events in the facet.
                        self.data.append(LogglyFacet(key, data[key]))
                else:
                    for item in data:
                        # Events are structured as the event text plus metadata about the event.
                        self.data.append(LogglyEvent(item))
            else:
                setattr(self, key, self.response_payload[key])


class LogglyEvent(object):
    """Loggly event. Makes Loggly events available as structured data."""

    isjson = None
    timestamp = None
    inputname = None
    inputid = None
    ip = None
    text = None

    def __init__(self, event):

        for key in event.keys():
            setattr(self, key, event[key])


class LogglyFacet(object):
    """Loggly facet. Makes Loggly facets available as structured data."""

    facet = None
    count = None

    def __init__(self, facet, count):

        self.facet = facet
        self.count = count


class LogglySearchContext(object):
    """Loggly search context. Makes Loggly search context available as structured data."""

    rows = None
    from_date = None
    until_date = None
    start = None
    query = None
    order = None

    def __init__(self, context):

        for key in context.keys():
            if key == 'from':
                self.from_date = context[key]
            elif key == 'until':
                self.until_date = context[key]
            else:
                setattr(self, key, context[key])