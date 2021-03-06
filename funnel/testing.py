# -*- coding: utf-8 -*-
#
# Copyright 2013 Unicon Pte. Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, with_statement

from discover import DiscoveringTestLoader
from funnel.queue import Manager
from optparse import OptionParser
import sys
from tornado.ioloop import IOLoop
from tornado.testing import AsyncTestCase
try:
    from unittest2 import TextTestRunner
except ImportError:
    from unittest import TextTestRunner
import types

HOST = '127.0.0.1'
class AsyncWorkerTestCase(AsyncTestCase):
    def setUp(self):
        super(AsyncWorkerTestCase, self).setUp()

        self.publisher = self.get_publisher()
        self.publisher.connect(host=HOST)
        self.publisher.start_consuming(self.stop, no_ack=True)
        self._worker = self.get_worker()
        self._worker.start(rpc=True, host=HOST)

    def get_publisher(self):
        return Manager()

    def get_worker(self):
        raise NotImplementedError()

    def get_new_ioloop(self):
        return IOLoop.current()

    def publish(self, message, **kwargs):
        if "routing_key" not in kwargs:
            kwargs["routing_key"] = self._worker.queue_name

        self.publisher.call(message, **kwargs)
        return self.wait()

    def doCleanups(self):
        self._worker.destruct()
        self.publisher.close_connection()
        super(AsyncWorkerTestCase, self).doCleanups()

# Copied from discover.py https://pypi.python.org/pypi/discover
if hasattr(types, 'ClassType'):
    class_types = (types.ClassType, type)
else:
    class_types = type

def _do_discovery(argv, verbosity, Loader):
    parser = OptionParser()
    parser.add_option('-v', '--verbose', dest='verbose', default=False,
                      help='Verbose output', action='store_true')
    parser.add_option('-s', '--start-directory', dest='start', default='funnel.tests',
                      help="Directory to start discovery ('funnel.tests' default)")
    parser.add_option('-p', '--pattern', dest='pattern', default='*.py',
                      help="Pattern to match tests ('*.py' default)")
    parser.add_option('-t', '--top-level-directory', dest='top', default=None,
                      help='Top level directory of project (defaults to start directory)')

    opts, args = parser.parse_args(argv)
    if len(args) > 3:
        _usage_exit()

    for name, value in zip(('start', 'pattern', 'top'), args):
        setattr(opts, name, value)

    if opts.verbose:
        verbosity = 2

    start_dir = opts.start
    pattern = opts.pattern
    top_level_dir = opts.top

    loader = Loader()
    return loader.discover(start_dir, pattern, top_level_dir), verbosity

def _run_tests(tests, testRunner, verbosity, exit):
    if isinstance(testRunner, class_types):
        try:
            testRunner = testRunner(verbosity=verbosity)
        except TypeError:
            # didn't accept the verbosity argument
            testRunner = testRunner()
    result = testRunner.run(tests)
    if exit:
        sys.exit(not result.wasSuccessful())
    return result

def main(argv=None, testRunner=None, testLoader=None, exit=True, verbosity=1):
    if testLoader is None:
        testLoader = DiscoveringTestLoader
    if testRunner is None:
        testRunner = TextTestRunner
    if argv is None:
        argv = sys.argv[1:]

    tests, verbosity = _do_discovery(argv, verbosity, testLoader)
    return _run_tests(tests, testRunner, verbosity, exit)
