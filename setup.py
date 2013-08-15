#!/usr/scripts/env python

# Copyright 2013 Jeff Vogelsang
# Copyright 2011 Electronic Arts Inc.
# 
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from distutils.core import setup

setup(name='eureka',
      version='0.13',
      description='A Python Loggly Library',
      long_description='Provides a Python interface to the Loggly API.',
      author='Jeff Vogelsang',
      author_email='jeffvogelsang@gmail.com',
      packages=['eureka'],
      requires=['requests (>=1.2.0)'],
      url='http://github.com/jeffvogelsang/eureka',
      license='Apache v2.0',
      platforms='Posix; MacOS X; Windows',
      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: System Administrators',
                   'License :: OSI Approved :: Apache Software License',
                   'Operating System :: OS Independent',
                   'Topic :: System :: Logging',
                   ]
      )