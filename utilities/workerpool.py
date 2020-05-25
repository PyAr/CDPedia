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

from twisted.internet import defer


class WorkerPool(object):
    """A twisted Worker Pool."""

    def __init__(self, size=30):
        self.size = size

    @defer.inlineCallbacks
    def _worker(self, function, iterable):
        """One worker instance."""
        while True:
            args = next(iterable)
            try:
                yield function(args)
            except Exception:
                pass

    def start(self, function, iterable):
        """Call the function for each set of args in iterable."""
        iterable = iter(iterable)
        workers = [self._worker(function, iterable) for n in range(self.size)]
        workers_d = defer.DeferredList(workers)
        return workers_d
