# -*- coding: utf-8 -*-

# Copyright 2010-2020 CDPedistas (see AUTHORS.txt)
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

"""Distribute tasks among a pool of threads."""

import queue
import threading
import time


# how much to sleep so that the while loop doesn't kill the processor
SLEEP = .3


class _Worker(threading.Thread):
    """Class used internally by the distributor.

    Run a function received from outside.
    """

    def __init__(self, num, function, queueInput, queueOutput, finish):
        self.me = num
        self.function = function
        self.qinp = queueInput
        self.qout = queueOutput
        self.finish = finish
        threading.Thread.__init__(self)

    def run(self):
        while True:
            info = self.qinp.get()
            if info == "quit":
                break
            res = self.function(info)
            self.finish.set()
            self.qout.put((info, res))


class Pool(object):
    """Build a pool of threads to distribute tasks.

    @param function: function to run
    @param quant: number of workers to open
    @param logf: function for logging mesages
    """

    def __init__(self, function, quant, logf=None):
        self._quantw = quant
        if logf is None:
            self.logf = lambda x: None
        else:
            self.logf = logf

        # launch n threads for each destiny
        self.qSend = [queue.Queue() for _ in range(self._quantw)]
        self.qReceive = [queue.Queue() for _ in range(self._quantw)]
        self.eFinish = [threading.Event() for _ in range(self._quantw)]
        for i in range(self._quantw):
            h = _Worker(i, function, self.qSend[i], self.qReceive[i], self.eFinish[i])
            h.start()
        self.logf("Created {} threads".format(quant))

    def process(self, tasks):
        """Process received tasks.

        Distribute tasks among workers, in parallel, while they're free.
        Return results as generator, with payload always at the beginning.

        @param tasks: all the tasks to run
        """

        # prepare tasks
        queued = tasks[:]
        queued.reverse()
        available = [True] * self._quantw

        # run while there's at least one pending task in the queue
        # or an unfinished destination
        while queued or sum(available) < self._quantw:
            self.logf("There are queued ({}) or unfinished tasks ({!r})"
                      .format(len(queued), available))

            # if there's a free thread give it a task (if any)
            while (queued and (True in available)):
                payload = queued.pop()
                free = available.index(True)
                q = self.qSend[free]
                q.put(payload)
                available[free] = False
                self.logf("Sent {!r} to thread {}".format(payload, free))

            # inspect pending tasks to see if any finished
            for i in range(self._quantw):
                if not self.eFinish[i].isSet():
                    continue

                # we have a result
                result = self.qReceive[i].get()
                self.eFinish[i].clear()
                self.logf("Received {!r} from thread {}".format(result, i))
                yield result
                available[i] = True

            # sleep a bit so that the while loop doesn't occupy the whole processor
            time.sleep(SLEEP)

        for q in self.qSend:
            q.put("quit")
        self.logf("quit signal sent to all threads.")
