# Copyright 2012-2020 CDPedistas (see AUTHORS.txt)
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# For further info, check  https://github.com/PyAr/CDPedia/

from twisted.internet import defer, reactor
from twisted.trial.unittest import TestCase

from utilities.workerpool import WorkerPool


class WorkerPoolTestCase(TestCase):
    """Test the WorkerPool class."""

    @defer.inlineCallbacks
    def test_start(self):
        """Test the WorkerPool.start class."""

        @defer.inlineCallbacks
        def squaring_processor(n):
            """A fake processor that squares."""
            d = defer.succeed(n ** 2)
            result = yield d
            results.append(result)

        wp = WorkerPool(3)
        results = []

        yield wp.start(squaring_processor, range(10))
        self.assertEqual(results, [n ** 2 for n in range(10)])
