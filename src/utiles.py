# -*- coding: utf8 -*-

'''Algunas pequeñas funciones útiles.'''

import re
import time
import socket
import threading

from hashlib import md5

import config

if hasattr(config, 'NAMESPACES'):
    # coincide si se empieza con uno de los namespaces más ~
    RE_NAMESPACES = re.compile(r'(%s):(.*)' % '|'.join(config.NAMESPACES))

def separaNombre(nombre):
    '''Devuelve (namespace, resto) de un nombre de archivo del wiki.'''
    m = RE_NAMESPACES.match(nombre)
    if not m:
        result = (None, nombre)
    else:
        result = m.groups()
    return result


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
        except socket.error, e:
            port += 1
        else:
            s.close()
            return port
