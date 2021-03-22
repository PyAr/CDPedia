# Copyright 2009-2020 CDPedistas (see AUTHORS.txt)
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

"""Some small utilities."""

import concurrent.futures
import logging
import queue
import os
import socket
import threading
import time
from hashlib import md5

import config

logger = logging.getLogger(__name__)


class WatchDog(threading.Thread):
    """Implementa un watchdog usando un thread.

    Una vez iniciado el watchdog se debe llamar al método update periódicamente a
    intervalos menores a sleep segundos para prevenir que el watchdog termine y
    llame al callback.

    En esta simple implementación el callback puede tardar hasta 2 veces sleep
    segundos en ser llamado.
    """
    def __init__(self, callback, sleep):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.callback = callback
        self.sleep = sleep
        self._tick = False

    def update(self):
        self._tick = False

    def run(self):
        while True:
            if self._tick:
                break
            self._tick = True
            time.sleep(self.sleep)
        self.callback()


def coherent_hash(txt):
    """
    Create a hash from a bytestring.

    This hash is multiplatform and the always the same for multiple Py versions.
    """
    return int(md5(txt).hexdigest()[-6:], 16)


def find_open_port(starting_from=8000, host="127.0.0.1"):
    """
    Finds a free port.
    """
    port = starting_from
    while 1:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except socket.error:
            port += 1
        else:
            s.close()
            return port


class TimingLogger:
    """Log only if more than N seconds passed after last log."""
    def __init__(self, secs_period, log_func):
        self._threshold = time.time() + secs_period
        self.log_func = log_func
        self.period = secs_period

    def log(self, *args, **kwargs):
        """Call log func with given args only if period exceeded."""
        if time.time() > self._threshold:
            self.log_func(*args, **kwargs)
            self._threshold = time.time() + self.period


class _StatusBoard:
    """Present the progress of the pooled executions."""

    def __init__(self, func, previous_count, known_errors):
        self.total = previous_count
        self.ok = previous_count
        self.bad = 0
        self.init_time = time.time()
        self.func = func
        self.known_errors = known_errors

    def process(self, payload):
        try:
            self.func(payload)
        except Exception as err:
            self.total += 1
            self.bad += 1
            if isinstance(err, self.known_errors):
                # show the error type, and the error message (which potentially would be
                # replaced with the msg args)
                template = "Known error {}: {}".format(err.__class__.__name__, err)
                logger.debug(template, *err.msg_args)
            else:
                logger.exception("Crashed while processing %r: %r", payload, err)
        else:
            self.total += 1
            self.ok += 1

        speed = self.total / (time.time() - self.init_time)

        # this is done through standard `print` to show progress nicely (if used logging it
        # will be too cumbersome to have one line per stat)
        stat = "Total={}  ok={}  bad={}  speed={:.2f} items/s\r".format(
            self.total, self.ok, self.bad, speed)
        print(stat, end='', flush=True)

    def finish(self):
        """Show final stats."""
        logger.info("Scraping done! Total=%s  ok=%s  bad=%s", self.total, self.ok, self.bad)


class _NotGreedyThreadPoolExecutor(concurrent.futures.ThreadPoolExecutor):
    """Patch TPE to not consume the source generator all at once."""

    def __init__(self, *args, **kwargs):
        super(_NotGreedyThreadPoolExecutor, self).__init__(*args, **kwargs)
        self._work_queue = queue.Queue(maxsize=kwargs['max_workers'] * 2)


def pooled_exec(func, previous_count, payloads, pool_size, known_errors=()):
    """Call func on each of the payloads, in a thread pool of indicated size.

    Present the progress nicely, counting also if function ended properly or not (if
    the error is known, log it in debug, else present the crash).
    """
    board = _StatusBoard(func, previous_count, tuple(known_errors))
    logger.info('Starting pooled exec! done before: %i,  total: %i',
                previous_count, previous_count + len(payloads))
    with _NotGreedyThreadPoolExecutor(max_workers=pool_size) as executor:
        # need to cosume the generator, but don't care about the results (board.process always
        # return None
        list(executor.map(board.process, payloads))
    board.finish()


def set_locale(second_language=None, record=False):
    """Set localization environment for gettext."""
    if config.LOCALE is not None:
        # running cdpedia from image
        os.environ['LANGUAGE'] = config.LOCALE
        return

    # running from project root directory
    if record:
        # running cdpetron, set locale and save it to file
        if config.LANGUAGE:
            os.environ['LANGUAGE'] = config.LANGUAGE
            if second_language:
                os.environ['LANGUAGE'] += ':' + second_language
            with open(config.LOG_LOCALE, 'wt', encoding='utf-8') as fh:
                fh.write(os.environ['LANGUAGE'])
    else:
        # running cdpedia, load locale from file
        with open(config.LOG_LOCALE, 'rt') as fh:
            os.environ['LANGUAGE'] = fh.read()
