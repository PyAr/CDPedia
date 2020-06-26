# -*- coding: utf8 -*-

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

import time
import socket
import threading

from hashlib import md5


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
    """Devuelve el mismo número en distintas versiones de Py y plataformas."""
    if isinstance(txt, str):
        txt = txt.encode("ascii")
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


class TimingLogger(object):
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
